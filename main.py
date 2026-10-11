import machine
import time
import sys
import select
from camera_uci import UCICamera
from buttons import Button

# ==============================================================================
# PIN DEFINITIONS & HARDWARE CONFIGURATION
# ==============================================================================

# UART Configuration
TX_PIN = 9           # ESP32 TX -> Camera RX 
RX_PIN = 10          # ESP32 RX <- Camera TX
UART_ID = 1          # Use UART 1
UART_BAUDRATE = 115200

# Push Buttons (PB)
PIN_PB1 = 6          # PB1 (Menu / Minus)
PIN_PB2 = 2          # PB2 (Action / Plus)

# External Status LED (moved to GPIO 3 to avoid the internal LED on GPIO 8)
PIN_STATUS_LED = 3   # Set to None if no LED is used

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
led = None
camera = None

def blink_led(times=1, duration_ms=50, gap_ms=150):
    """Briefly blinks status LED to give feedback."""
    global led
    if led:
        try:
            for _ in range(times):
                led.value(1)  # 1 = ON (External LED prijungtas prie GND)
                time.sleep_ms(duration_ms)
                led.value(0)  # 0 = OFF
                if times > 1:
                    time.sleep_ms(gap_ms)
        except Exception:
            pass

# ==============================================================================
# BUTTON ACTION HANDLERS
# ==============================================================================

def on_pb1_click(btn):
    # PB1 Short Click -> NUC (if Normal) or Minus (if Settings)
    if active_mode == MODE_NORMAL:
        print("[PB1 Short] -> Shutter Calibration (NUC)")
        camera.calibrate()
    elif active_mode == MODE_BRIGHTNESS:
        print(f"[PB1 Short] -> Brightness -{BRIGHTNESS_STEP}")
        camera.adjust_brightness(-BRIGHTNESS_STEP)
    elif active_mode == MODE_CONTRAST:
        print(f"[PB1 Short] -> Contrast -{CONTRAST_STEP}")
        camera.adjust_contrast(-CONTRAST_STEP)
    elif active_mode == MODE_ENHANCEMENT:
        print(f"[PB1 Short] -> Enhancement -{ENHANCEMENT_STEP}")
        camera.adjust_enhancement(-ENHANCEMENT_STEP)

def on_pb1_long_press(btn):
    # PB1 Long Press -> Cycle Modes (Normal -> Brightness -> Contrast -> Enhancement -> Normal)
    global active_mode
    active_mode = (active_mode + 1) % len(MODE_NAMES)
    
    print(f"\n[{'='*40}]")
    print(f"MODE CHANGED: >>> {MODE_NAMES[active_mode]} <<<")
    print(f"[{'='*40}]\n")
    
    if active_mode == MODE_NORMAL:
        # Long solid blink for normal mode
        blink_led(times=1, duration_ms=400, gap_ms=0)
    else:
        # Blink 1, 2, or 3 times for the respective settings mode
        blink_led(times=active_mode, duration_ms=100, gap_ms=200)

def on_pb2_click(btn):
    # PB2 Short Click -> Zoom (if Normal) or Plus (if Settings)
    if active_mode == MODE_NORMAL:
        next_zoom = (camera.current_zoom_idx + 1) % len(camera.ZOOM_LEVELS)
        print(f"[PB2 Short] -> Cycling Zoom to preset {next_zoom}")
        camera.set_zoom(next_zoom)
    elif active_mode == MODE_BRIGHTNESS:
        print(f"[PB2 Short] -> Brightness +{BRIGHTNESS_STEP}")
        camera.adjust_brightness(BRIGHTNESS_STEP)
    elif active_mode == MODE_CONTRAST:
        print(f"[PB2 Short] -> Contrast +{CONTRAST_STEP}")
        camera.adjust_contrast(CONTRAST_STEP)
    elif active_mode == MODE_ENHANCEMENT:
        print(f"[PB2 Short] -> Enhancement +{ENHANCEMENT_STEP}")
        camera.adjust_enhancement(ENHANCEMENT_STEP)

def on_pb2_long_press(btn):
    # PB2 Long Press -> Palette Cycle (only in Normal mode)
    if active_mode == MODE_NORMAL:
        print("\n[PB2 Long] -> Cycling Color Palette")
        camera.next_palette()
    else:
        print("\n[PB2 Long] -> Ignored in Settings mode")

# ==============================================================================
# MAIN INITIALIZATION & RUN LOOP
# ==============================================================================

def main():
    global camera, led
    print("=" * 60)
    print("ESP32-C3 NVG Thermal Camera Controller Starting...")
    print("Protocol: UCI (55 43 49)")
    print("Interface: 2-Button Minimalist UI")
    print("=" * 60)

    # Force internal ESP32 LED (GPIO 8) OFF so it doesn't irritate the eyes
    try:
        machine.Pin(8, machine.Pin.OUT).value(1)
    except Exception:
        pass

    # Initialize external status LED
    if PIN_STATUS_LED is not None:
        try:
            led = machine.Pin(PIN_STATUS_LED, machine.Pin.OUT)
            led.value(0)  # Default off (active-high logic)
        except Exception as e:
            print(f"[Warning] Could not initialize LED on GPIO{PIN_STATUS_LED}: {e}")
            led = None

    # Initialize Camera Driver
    camera = UCICamera(
        uart_id=UART_ID,
        tx_pin=TX_PIN,
        rx_pin=RX_PIN,
        baudrate=UART_BAUDRATE,
        debug=True
    )

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

    print("\nButtons Initialized:")
    print("  PB1 (GPIO 6) - MENU / MINUS:")
    print("    * Normal Mode: Short -> NUC Calibrate  | Long -> Enter Settings Mode")
    print("    * Setup Mode:  Short -> Value -        | Long -> Next Setting Mode")
    print("  PB2 (GPIO 2) - ACTION / PLUS:")
    print("    * Normal Mode: Short -> Cycle Zoom     | Long -> Cycle Palette")
    print("    * Setup Mode:  Short -> Value +        | Long -> (Ignored)")
    print(f"\nInitial Mode: {MODE_NAMES[active_mode]}")
    print("Listening for button events and UART data...\n")

    # Set up console input polling
    poll_obj = select.poll()
    poll_obj.register(sys.stdin, select.POLLIN)
    input_buffer = ""

    # Brief startup delay
    time.sleep_ms(300)

    # Main non-blocking event loop
    while True:
        # Check buttons
        for b in buttons:
            b.update()

        # Check for UART input from Camera (unsolicited or response)
        if camera.uart.any():
            buf = camera.uart.read(camera.uart.any())
            if buf:
                hex_str = " ".join(f"{b:02X}" for b in buf)
                print(f"[CAM RX]: {hex_str}")

        # Check for terminal input (manual hex commands)
        if poll_obj.poll(0):
            char = sys.stdin.read(1)
            if char == '\n' or char == '\r':
                if input_buffer.strip():
                    try:
                        hex_bytes = bytes.fromhex(input_buffer)
                        print(f"[Manual TX] {input_buffer.strip().upper()}")
                        camera.send_raw(hex_bytes)
                        # We let the main loop catch the [CAM RX] response
                    except ValueError:
                        print("[Error] Invalid hex format. Type pairs of hex digits (e.g., '23 57 66').")
                    input_buffer = ""
            else:
                input_buffer += char

        # Small delay to yield to RTOS watchdogs and save power (Light Sleep)
        time.sleep_ms(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[System] Halted by user (KeyboardInterrupt).")
