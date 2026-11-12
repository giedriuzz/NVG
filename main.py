import machine
import time
from camera_uci import UCICamera
from buttons import Button

# ==============================================================================
# PIN DEFINITIONS & HARDWARE CONFIGURATION
# ==============================================================================

# Debug Mode (False = fast & silent for battery operation; True = USB Serial logs & hex input)
DEBUG = False

# UART Configuration
TX_PIN = 9           # ESP32 TX -> Camera RX 
RX_PIN = 10          # ESP32 RX <- Camera TX
UART_ID = 1          # Use UART 1
UART_BAUDRATE = 115200

# Push Buttons (PB)
PIN_PB1 = 6          # PB1 (Menu / Minus)
PIN_PB2 = 2          # PB2 (Action / Plus)

# External Status LED (moved to GPIO 3 to avoid the internal LED on GPIO 8)
PIN_STATUS_LED: "int | None" = 3   # Set to None if no LED is used

# Battery Voltage Monitoring (10k + 10k Voltage Divider -> GPIO 4)
PIN_BATTERY_ADC: "int | None" = 4  # ADC1 pin (GPIO 0, 1, or 4)
BATTERY_DIVIDER_RATIO = 2.0  # (10k + 10k) / 10k = 2.0
LOW_BATTERY_VOLTAGE = 3.40   # Trigger gentle LED pulsing below this voltage (V)
LOW_BATTERY_RECOVERY = 3.55  # Stop pulsing when voltage rises above this (hysteresis)
MIN_VALID_BATTERY_V = 2.00   # Ignore readings below 2.0V (e.g. when running on USB without battery)
BATTERY_CHECK_MS = 5000      # Check battery every 5 seconds

# LED Breathing (Pulse) Configuration for Low Battery
PULSE_PERIOD_MS = 2400       # Full breathe-in + breathe-out cycle duration in ms
PULSE_MAX_DUTY = 45000       # Peak brightness during pulse (0..65535)

# Wi-Fi OTA Update Configuration (activated by holding PB2 during power-on)
OTA_WIFI_SSID = "NVG-OTA"
OTA_WIFI_PASSWORD = "nvgupdate"  # Minimum 8 characters for WPA2 (or "" for open AP)
OTA_BOOT_HOLD_MS = 1000          # Hold PB2 (or PB1+PB2) for 1s at boot to enter OTA mode

# Electrical Configuration
BUTTONS_ACTIVE_LOW = True  # True: Button connects pin to GND when pressed (internal pull-up)
DEBOUNCE_MS = 35           # Debounce filter time in milliseconds
LONG_PRESS_MS = 600        # Long press detection threshold in milliseconds (shortened slightly for better feel)

# Adjustment Step Sizes
BRIGHTNESS_STEP = 15
CONTRAST_STEP = 15
ENHANCEMENT_STEP = 15

# ==============================================================================
# APPLICATION STATE & MODES
# ==============================================================================

MODE_NORMAL = 0
MODE_BRIGHTNESS = 1
MODE_CONTRAST = 2
MODE_ENHANCEMENT = 3

MODE_NAMES = ["NORMAL (Zoom/NUC)", "BRIGHTNESS", "CONTRAST", "IMAGE ENHANCEMENT"]

active_mode = MODE_NORMAL
led_pwm: "machine.PWM | None" = None
adc_bat: "machine.ADC | None" = None
camera: "UCICamera | None" = None
low_battery_active = False

def set_led_duty(duty_u16: int):
    """Sets LED brightness using 16-bit PWM duty (0..65535)."""
    global led_pwm
    if led_pwm:
        try:
            led_pwm.duty_u16(duty_u16)
        except Exception:
            pass

def blink_led(times=1, duration_ms=50, gap_ms=150):
    """Briefly blinks status LED to give feedback, temporarily overriding any pulse."""
    global led_pwm
    if led_pwm:
        try:
            if low_battery_active:
                led_pwm.duty_u16(0)
                time.sleep_ms(100)
            for _ in range(times):
                led_pwm.duty_u16(65535)  # Full ON (External LED prijungtas prie GND)
                time.sleep_ms(duration_ms)
                led_pwm.duty_u16(0)      # OFF
                if times > 1:
                    time.sleep_ms(gap_ms)
            if low_battery_active:
                time.sleep_ms(100)
        except Exception:
            pass

def update_led_pulse(now_ms: int):
    """Updates smooth quadratic breathing effect on LED when battery is low."""
    if not led_pwm or not low_battery_active:
        return
    half_period = PULSE_PERIOD_MS // 2
    pos = now_ms % PULSE_PERIOD_MS
    if pos > half_period:
        pos = PULSE_PERIOD_MS - pos
    # Quadratic curve (pos^2) for smooth eye-perceived fade-in and fade-out
    duty = (pos * pos * PULSE_MAX_DUTY) // (half_period * half_period)
    set_led_duty(duty)

def read_battery_voltage(samples=16) -> float:
    """Reads averaged battery voltage in Volts using factory-calibrated read_uv()."""
    if not adc_bat:
        return 0.0
    total_uv = 0
    for _ in range(samples):
        total_uv += adc_bat.read_uv()
    pin_v = (total_uv / samples) / 1_000_000.0
    return pin_v * BATTERY_DIVIDER_RATIO

def check_battery():
    """Checks battery voltage and toggles low-battery LED pulsing with hysteresis."""
    global low_battery_active
    if not adc_bat:
        return
    v_bat = read_battery_voltage()
    if v_bat < MIN_VALID_BATTERY_V:
        # Divider disconnected or running purely off USB without battery
        if low_battery_active:
            low_battery_active = False
            set_led_duty(0)
        return

    if not low_battery_active and v_bat <= LOW_BATTERY_VOLTAGE:
        low_battery_active = True
        if DEBUG:
            print(f"[Battery] LOW BATTERY WARNING: {v_bat:.2f}V (LED pulsing enabled)")
    elif low_battery_active and v_bat >= LOW_BATTERY_RECOVERY:
        low_battery_active = False
        set_led_duty(0)
        if DEBUG:
            print(f"[Battery] Battery recovered: {v_bat:.2f}V (LED pulsing stopped)")

# ==============================================================================
# BUTTON ACTION HANDLERS
# ==============================================================================

def on_pb1_click(btn):
    # PB1 Short Click -> NUC (if Normal) or Minus (if Settings)
    if camera is None:
        return
    if active_mode == MODE_NORMAL:
        if DEBUG:
            print("[PB1 Short] -> Shutter Calibration (NUC)")
        camera.calibrate()
    elif active_mode == MODE_BRIGHTNESS:
        if DEBUG:
            print(f"[PB1 Short] -> Brightness -{BRIGHTNESS_STEP}")
        camera.adjust_brightness(-BRIGHTNESS_STEP)
    elif active_mode == MODE_CONTRAST:
        if DEBUG:
            print(f"[PB1 Short] -> Contrast -{CONTRAST_STEP}")
        camera.adjust_contrast(-CONTRAST_STEP)
    elif active_mode == MODE_ENHANCEMENT:
        if DEBUG:
            print(f"[PB1 Short] -> Enhancement -{ENHANCEMENT_STEP}")
        camera.adjust_enhancement(-ENHANCEMENT_STEP)

def on_pb1_long_press(btn):
    # PB1 Long Press -> Cycle Modes (Normal -> Brightness -> Contrast -> Enhancement -> Normal)
    global active_mode
    active_mode = (active_mode + 1) % len(MODE_NAMES)
    
    if DEBUG:
        print(f"MODE CHANGED: >>> {MODE_NAMES[active_mode]} <<<")
    
    if active_mode == MODE_NORMAL:
        # Long solid blink for normal mode
        blink_led(times=1, duration_ms=400, gap_ms=0)
    else:
        # Blink 1, 2, or 3 times for the respective settings mode
        blink_led(times=active_mode, duration_ms=100, gap_ms=200)

def on_pb2_click(btn):
    # PB2 Short Click -> Zoom (if Normal) or Plus (if Settings)
    if camera is None:
        return
    if active_mode == MODE_NORMAL:
        next_zoom = (camera.current_zoom_idx + 1) % len(camera.ZOOM_LEVELS)
        if DEBUG:
            print(f"[PB2 Short] -> Cycling Zoom to preset {next_zoom}")
        camera.set_zoom(next_zoom)
    elif active_mode == MODE_BRIGHTNESS:
        if DEBUG:
            print(f"[PB2 Short] -> Brightness +{BRIGHTNESS_STEP}")
        camera.adjust_brightness(BRIGHTNESS_STEP)
    elif active_mode == MODE_CONTRAST:
        if DEBUG:
            print(f"[PB2 Short] -> Contrast +{CONTRAST_STEP}")
        camera.adjust_contrast(CONTRAST_STEP)
    elif active_mode == MODE_ENHANCEMENT:
        if DEBUG:
            print(f"[PB2 Short] -> Enhancement +{ENHANCEMENT_STEP}")
        camera.adjust_enhancement(ENHANCEMENT_STEP)

def on_pb2_long_press(btn):
    # PB2 Long Press -> Palette Cycle (only in Normal mode)
    if camera is None:
        return
    if active_mode == MODE_NORMAL:
        if DEBUG:
            print("[PB2 Long] -> Cycling Color Palette")
        camera.next_palette()
    elif DEBUG:
        print("[PB2 Long] -> Ignored in Settings mode")

# ==============================================================================
# MAIN INITIALIZATION & RUN LOOP
# ==============================================================================

def main():
    global camera, led_pwm, adc_bat
    if DEBUG:
        print("ESP32-C3 NVG Thermal Camera Controller Starting...")

    # Force internal ESP32 LED (GPIO 8) OFF so it doesn't irritate the eyes
    try:
        machine.Pin(8, machine.Pin.OUT).value(1)
    except Exception:
        pass

    # Initialize external status LED with PWM (for both blinking and gentle pulsing)
    if PIN_STATUS_LED is not None:
        try:
            led_pwm = machine.PWM(machine.Pin(PIN_STATUS_LED), freq=1000, duty_u16=0)
        except Exception as e:
            if DEBUG:
                print(f"[Warning] Could not initialize PWM LED on GPIO{PIN_STATUS_LED}: {e}")
            led_pwm = None

    # Initialize Battery ADC (10k + 10k divider)
    if PIN_BATTERY_ADC is not None:
        try:
            adc_bat = machine.ADC(machine.Pin(PIN_BATTERY_ADC))
            adc_bat.atten(machine.ADC.ATTN_11DB)
            if DEBUG:
                v_init = read_battery_voltage()
                print(f"[Battery] Initialized ADC on GPIO{PIN_BATTERY_ADC} (Current: {v_init:.2f}V)")
            check_battery()
        except Exception as e:
            if DEBUG:
                print(f"[Warning] Could not initialize Battery ADC on GPIO{PIN_BATTERY_ADC}: {e}")
            adc_bat = None

    # Initialize Buttons
    pb1 = Button(PIN_PB1, name="PB1 (GPIO6)", active_low=BUTTONS_ACTIVE_LOW,
                 debounce_ms=DEBOUNCE_MS, long_press_ms=LONG_PRESS_MS)
    pb1.on_click = on_pb1_click
    pb1.on_long_press = on_pb1_long_press

    pb2 = Button(PIN_PB2, name="PB2 (GPIO2)", active_low=BUTTONS_ACTIVE_LOW,
                 debounce_ms=DEBOUNCE_MS, long_press_ms=LONG_PRESS_MS)
    pb2.on_click = on_pb2_click
    pb2.on_long_press = on_pb2_long_press

    buttons = [pb1, pb2]

    # Check if PB2 (or PB1+PB2) is held at power-on to enter Wi-Fi OTA Update Mode
    if pb2._read_is_pressed():
        if DEBUG:
            print(f"[Boot] PB2 held at startup. Hold for {OTA_BOOT_HOLD_MS}ms to enter OTA Mode...")
        ota_triggered = True
        start_hold = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_hold) < OTA_BOOT_HOLD_MS:
            if not pb2._read_is_pressed():
                ota_triggered = False
                break
            time.sleep_ms(20)

        if ota_triggered:
            from ota_server import run_ota_portal
            run_ota_portal(
                ssid=OTA_WIFI_SSID,
                password=OTA_WIFI_PASSWORD,
                set_led_duty=set_led_duty,
                read_battery_fn=read_battery_voltage,
                debug=DEBUG
            )
            return

    # Normal operation: explicitly disable Wi-Fi to save battery power
    try:
        from ota_server import disable_wifi
        disable_wifi()
    except Exception:
        pass

    # Initialize Camera Driver
    camera = UCICamera(
        uart_id=UART_ID,
        tx_pin=TX_PIN,
        rx_pin=RX_PIN,
        baudrate=UART_BAUDRATE,
        debug=DEBUG
    )

    poll_obj = None
    input_buffer = ""
    if DEBUG:
        import sys
        import select
        print(f"Initial Mode: {MODE_NAMES[active_mode]}")
        poll_obj = select.poll()
        poll_obj.register(sys.stdin, select.POLLIN)

    # Brief startup delay
    time.sleep_ms(300)
    last_bat_check_ms = time.ticks_ms()

    # Main non-blocking event loop
    while True:
        now_ms = time.ticks_ms()

        # Check buttons
        for b in buttons:
            b.update(now_ms)

        # Periodic battery check
        if time.ticks_diff(now_ms, last_bat_check_ms) >= BATTERY_CHECK_MS:
            last_bat_check_ms = now_ms
            check_battery()

        # Update gentle LED breathing if battery is low
        if low_battery_active:
            update_led_pulse(now_ms)

        # Check for UART input from Camera
        if camera.uart.any():
            buf = camera.uart.read(camera.uart.any())
            if DEBUG and buf:
                hex_str = " ".join(f"{b:02X}" for b in buf)
                print(f"[CAM RX]: {hex_str}")

        # Check for terminal input (manual hex commands - only in DEBUG mode)
        if DEBUG and poll_obj and poll_obj.poll(0):
            import sys
            char = sys.stdin.read(1)
            if char == '\n' or char == '\r':
                if input_buffer.strip():
                    try:
                        hex_bytes = bytes.fromhex(input_buffer)
                        print(f"[Manual TX] {input_buffer.strip().upper()}")
                        camera.send_raw(hex_bytes)
                    except ValueError:
                        print("[Error] Invalid hex format.")
                    input_buffer = ""
            else:
                input_buffer += char

        # Small delay to yield to RTOS watchdogs and save power (Light Sleep)
        time.sleep_ms(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        if DEBUG:
            print("\n[System] Halted by user (KeyboardInterrupt).")
