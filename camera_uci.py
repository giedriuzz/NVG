import machine
import time

class UCICamera:
    PALETTES = {
        0: b'\x55\x43\x49\x12\x00\x10\x03\x45\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x54\x6D', # White Hot
        1: b'\x55\x43\x49\x12\x00\x10\x03\x45\x00\x00\x0A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x69\x6F', # Black Hot
    }

    ZOOM_LEVELS = [
        b'\x55\x43\x49\x12\x00\x01\x31\x42\x00\x00\x0A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x0A', # 1.0x
        b'\x55\x43\x49\x12\x00\x01\x31\x42\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x41\x0C', # 2.0x
        b'\x55\x43\x49\x12\x00\x01\x31\x42\x00\x00\x1E\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x7C\x0E', # 3.0x
        b'\x55\x43\x49\x12\x00\x01\x31\x42\x00\x00\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xCF\x00', # 4.0x
        b'\x55\x43\x49\x12\x00\x01\x31\x42\x00\x00\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xD3\x19', # 8.0x
    ]

    BRIGHTNESS_LEVELS = [
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xE3', # 0
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x85\xD9', # 20
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x96', # 40
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x3C\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8D\xAC', # 60
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11\x09', # 80
        b'\x55\x43\x49\x12\x00\x10\x04\x47\x00\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x35\x5D', # 100
    ]

    CONTRAST_LEVELS = [
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xAE\x8E', # 0
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x2A\xB4', # 20
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xA6\xFB', # 40
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x3C\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x22\xC1', # 60
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xBE\x64', # 80
        b'\x55\x43\x49\x12\x00\x10\x04\x4A\x00\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x9A\x30', # 100
    ]

    ENHANCEMENT_LEVELS = [
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xC3\x15', # 0
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x47\x2F', # 20
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xCB\x60', # 40
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x3C\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x4F\x5A', # 60
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xD3\xFF', # 80
        b'\x55\x43\x49\x12\x00\x10\x04\x45\x00\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xF7\xAB', # 100
    ]

    def __init__(self, uart_id=1, tx_pin=9, rx_pin=10, baudrate=115200, debug=True):
        self.debug = debug
        self.uart = machine.UART(
            uart_id,
            baudrate=baudrate,
            tx=machine.Pin(tx_pin),
            rx=machine.Pin(rx_pin),
            timeout=100
        )
        self.current_zoom_idx = 0
        self.current_palette = 0
        self.current_brightness_idx = 2
        self.current_contrast_idx = 2
        self.current_enhancement_idx = 2
        self.auto_calib_enabled = True

        if self.debug:
            print(f"[UCICamera] Initialized UART{uart_id} at {baudrate} baud")

    def _format_hex(self, data: bytes) -> str:
        return " ".join(f"{b:02X}" for b in data)

    def send_raw(self, frame: bytes) -> int:
        if self.debug:
            print(f"[TX] {self._format_hex(frame)}")
        return self.uart.write(frame)

    def read_response(self, timeout_ms=300) -> bytes:
        start = time.ticks_ms()
        buf = bytearray()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if self.uart.any():
                chunk = self.uart.read(self.uart.any())
                if chunk:
                    buf.extend(chunk)
            time.sleep_ms(5)
            
        if buf and self.debug:
            print(f"[RX] {self._format_hex(buf)}")
        return bytes(buf)

    def calibrate(self):
        cmd = b'\x55\x43\x49\x12\x00\x10\x02\x43\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xCF\xC8'
        print("[UCICamera] Executing Shutter Calibration (NUC)...")
        self.send_raw(cmd)
        return self.read_response(500)

    def set_palette(self, index: int):
        index = max(0, min(len(self.PALETTES) - 1, index))
        self.current_palette = index
        print(f"[UCICamera] Palette set to index {index}")
        self.send_raw(self.PALETTES[index])
        return self.read_response()

    def next_palette(self):
        next_idx = (self.current_palette + 1) % len(self.PALETTES)
        return self.set_palette(next_idx)

    def set_zoom(self, idx: int):
        idx = max(0, min(len(self.ZOOM_LEVELS) - 1, idx))
        self.current_zoom_idx = idx
        print(f"[UCICamera] Zoom set to preset {idx}")
        self.send_raw(self.ZOOM_LEVELS[idx])
        return self.read_response()

    def zoom_in(self):
        return self.set_zoom(self.current_zoom_idx + 1)

    def zoom_out(self):
        return self.set_zoom(self.current_zoom_idx - 1)

    def adjust_brightness(self, delta: int):
        direction = 1 if delta > 0 else -1
        idx = max(0, min(len(self.BRIGHTNESS_LEVELS) - 1, self.current_brightness_idx + direction))
        self.current_brightness_idx = idx
        print(f"[UCICamera] Brightness set to preset {idx}")
        self.send_raw(self.BRIGHTNESS_LEVELS[idx])
        return self.read_response()

    def adjust_contrast(self, delta: int):
        direction = 1 if delta > 0 else -1
        idx = max(0, min(len(self.CONTRAST_LEVELS) - 1, self.current_contrast_idx + direction))
        self.current_contrast_idx = idx
        print(f"[UCICamera] Contrast set to preset {idx}")
        self.send_raw(self.CONTRAST_LEVELS[idx])
        return self.read_response()

    def adjust_enhancement(self, delta: int):
        direction = 1 if delta > 0 else -1
        idx = max(0, min(len(self.ENHANCEMENT_LEVELS) - 1, self.current_enhancement_idx + direction))
        self.current_enhancement_idx = idx
        print(f"[UCICamera] Enhancement set to preset {idx}")
        self.send_raw(self.ENHANCEMENT_LEVELS[idx])
        return self.read_response()

    def toggle_auto_calibration(self):
        cmd = b'\x55\x43\x49\x12\x00\x10\x02\x41\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x78\x3D' # Auto on
        if self.auto_calib_enabled:
            cmd = b'\x55\x43\x49\x12\x00\x10\x02\x41\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0D\x3E' # Auto off
        self.auto_calib_enabled = not self.auto_calib_enabled
        print(f"[UCICamera] Auto calibration {'ON' if self.auto_calib_enabled else 'OFF'}")
        self.send_raw(cmd)
        return self.read_response()

    def sync_parameters(self):
        print("[UCICamera] Skipping sync_parameters for now.")
        pass

    def query_image_parameters(self):
        print("[UCICamera] Query parameters not mapped yet.")
        pass
