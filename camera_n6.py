"""
N6 Thermal Camera UART Driver for MicroPython (ESP32-C3)
Protocol specification based on 'N6 UART command file 90 proc kad mano.xlsx'

Frame format:
- Write frame: 0x23 0x57 [CMD] [LEN/SUB] [DATA...] 0x45 0x4E 0x44  (#W...END)
- Read frame:  0x23 0x52 [CMD] [LEN/SUB] [DATA...] 0x45 0x4E 0x44  (#R...END)
"""

import machine
import time

class N6Camera:
    # Frame delimiters
    HEADER_WRITE = b'\x23\x57'  # '#W'
    HEADER_READ  = b'\x23\x52'  # '#R'
    FOOTER       = b'\x45\x4E\x44'  # 'END'

    # Palette names
    PALETTES = [
        "White Hot",    # 0x00
        "Black Hot",    # 0x01
        "Iron Oxide Red", # 0x02
        "Red Hot",      # 0x03
        "Green Light",  # 0x04
    ]

    def __init__(self, uart_id=1, tx_pin=21, rx_pin=20, baudrate=115200, debug=True):
        self.debug = debug
        self.uart = machine.UART(
            uart_id,
            baudrate=baudrate,
            tx=machine.Pin(tx_pin),
            rx=machine.Pin(rx_pin),
            timeout=100
        )
        
        # Internal state tracking
        self.current_zoom = 1           # 1x to 8x
        self.current_palette = 0        # 0 to 4
        self.current_brightness = 128   # 1 to 255
        self.current_contrast = 128     # 1 to 255
        self.current_enhancement = 128  # 1 to 255
        self.auto_calib_enabled = True

        if self.debug:
            print(f"[N6Camera] Initialized UART{uart_id} (TX=GPIO{tx_pin}, RX=GPIO{rx_pin}, {baudrate} baud)")

    def _format_hex(self, data: bytes) -> str:
        return " ".join(f"{b:02X}" for b in data)

    def send_raw(self, frame: bytes) -> int:
        """Sends raw command frame to camera."""
        if self.debug:
            print(f"[TX] {self._format_hex(frame)}")
        return self.uart.write(frame)

    def read_response(self, timeout_ms=300) -> bytes:
        """Reads response frame ending with END if available."""
        start = time.ticks_ms()
        buf = bytearray()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if self.uart.any():
                chunk = self.uart.read(self.uart.any())
                if chunk:
                    buf.extend(chunk)
                    if buf.endswith(self.FOOTER):
                        break
            time.sleep_ms(5)
            
        if buf and self.debug:
            print(f"[RX] {self._format_hex(buf)}")
        return bytes(buf)

    # ------------------ Core Camera Commands ------------------ #

    def calibrate(self):
        """
        File calibration (NUC / Shutter correction operation).
        Command: 23 57 05 01 00 05 00 45 4E 44
        """
        cmd = self.HEADER_WRITE + b'\x05\x01\x00\x05\x00' + self.FOOTER
        print("[N6Camera] Executing Shutter Calibration (NUC)...")
        self.send_raw(cmd)
        return self.read_response(500)

    def set_palette(self, index: int):
        """
        Set pseudo-color palette:
        0: White Hot, 1: Black Hot, 2: Iron Oxide Red, 3: Red Hot, 4: Green Light.
        Command: 23 57 23 02 00 [index] 00 00 45 4E 44
        """
        index = max(0, min(len(self.PALETTES) - 1, index))
        self.current_palette = index
        cmd = self.HEADER_WRITE + bytes([0x23, 0x02, 0x00, index, 0x00, 0x00]) + self.FOOTER
        print(f"[N6Camera] Palette set to [{index}] {self.PALETTES[index]}")
        self.send_raw(cmd)
        return self.read_response()

    def next_palette(self):
        """Cycle to the next pseudo-color palette."""
        next_idx = (self.current_palette + 1) % len(self.PALETTES)
        return self.set_palette(next_idx)

    def set_zoom(self, level: int):
        """
        Electronic magnification (1x to 8x).
        Command: 23 57 44 02 00 [level] 00 00 45 4E 44
        """
        level = max(1, min(8, level))
        self.current_zoom = level
        cmd = self.HEADER_WRITE + bytes([0x44, 0x02, 0x00, level, 0x00, 0x00]) + self.FOOTER
        print(f"[N6Camera] Zoom set to {level}x")
        self.send_raw(cmd)
        return self.read_response()

    def zoom_in(self):
        """Increase magnification by 1 step (max 8x)."""
        if self.current_zoom < 8:
            return self.set_zoom(self.current_zoom + 1)
        else:
            print("[N6Camera] Already at maximum zoom (8x)")
            return None

    def zoom_out(self):
        """Decrease magnification by 1 step (min 1x)."""
        if self.current_zoom > 1:
            return self.set_zoom(self.current_zoom - 1)
        else:
            print("[N6Camera] Already at minimum zoom (1x)")
            return None

    def set_brightness(self, value: int):
        """
        Set brightness (1 <= value <= 255).
        Command: 23 57 99 02 00 00 [value] 00 45 4E 44
        """
        value = max(1, min(255, value))
        self.current_brightness = value
        cmd = self.HEADER_WRITE + bytes([0x99, 0x02, 0x00, 0x00, value, 0x00]) + self.FOOTER
        print(f"[N6Camera] Brightness set to {value}/255")
        self.send_raw(cmd)
        return self.read_response()

    def adjust_brightness(self, delta: int):
        """Adjust brightness relative to current value."""
        return self.set_brightness(self.current_brightness + delta)

    def set_contrast(self, value: int):
        """
        Set contrast (1 <= value <= 255).
        Command: 23 57 99 02 00 01 [value] 00 45 4E 44
        """
        value = max(1, min(255, value))
        self.current_contrast = value
        cmd = self.HEADER_WRITE + bytes([0x99, 0x02, 0x00, 0x01, value, 0x00]) + self.FOOTER
        print(f"[N6Camera] Contrast set to {value}/255")
        self.send_raw(cmd)
        return self.read_response()

    def adjust_contrast(self, delta: int):
        """Adjust contrast relative to current value."""
        return self.set_contrast(self.current_contrast + delta)

    def set_enhancement(self, value: int):
        """
        Set image enhancement (1 <= value <= 255).
        Command: 23 57 99 02 00 03 [value] 00 45 4E 44
        """
        value = max(1, min(255, value))
        self.current_enhancement = value
        cmd = self.HEADER_WRITE + bytes([0x99, 0x02, 0x00, 0x03, value, 0x00]) + self.FOOTER
        print(f"[N6Camera] Enhancement set to {value}/255")
        self.send_raw(cmd)
        return self.read_response()

    def adjust_enhancement(self, delta: int):
        """Adjust enhancement relative to current value."""
        return self.set_enhancement(self.current_enhancement + delta)

    def set_auto_calibration(self, enabled: bool):
        """
        Automatic calibration:
        ON:  23 57 67 02 00 0D 00 00 45 4E 44
        OFF: 23 57 67 02 00 01 00 00 45 4E 44
        """
        self.auto_calib_enabled = enabled
        sub = 0x0D if enabled else 0x01
        cmd = self.HEADER_WRITE + bytes([0x67, 0x02, 0x00, sub, 0x00, 0x00]) + self.FOOTER
        state_str = "ENABLED" if enabled else "DISABLED"
        print(f"[N6Camera] Auto calibration {state_str}")
        self.send_raw(cmd)
        return self.read_response()

    def toggle_auto_calibration(self):
        """Toggle automatic calibration on/off."""
        return self.set_auto_calibration(not self.auto_calib_enabled)

    def sync_parameters(self):
        """
        Parameter synchronization to upper computer.
        Command: 23 57 66 02 00 00 00 00 45 4E 44
        """
        cmd = self.HEADER_WRITE + b'\x66\x02\x00\x00\x00\x00' + self.FOOTER
        print("[N6Camera] Synchronizing parameters...")
        self.send_raw(cmd)
        return self.read_response()

    def query_image_parameters(self):
        """
        Query Brightness/Contrast/Enhancement.
        Command: 23 52 9A 01 00 00 00 45 4E 44
        Response format: 23 52 9A 59 05 00 X1 X2 00 X3 00 00 45 4E 44
        """
        cmd = self.HEADER_READ + b'\x9A\x01\x00\x00\x00' + self.FOOTER
        print("[N6Camera] Querying Brightness/Contrast/Enhancement...")
        self.send_raw(cmd)
        resp = self.read_response(500)
        if len(resp) >= 14 and resp.startswith(self.HEADER_READ + b'\x9A\x59'):
            # X1: brightness, X2: contrast, X3: enhancement
            b = resp[6]
            c = resp[7]
            e = resp[9]
            self.current_brightness = b
            self.current_contrast = c
            self.current_enhancement = e
            print(f"[N6Camera] Query result -> Brightness: {b}, Contrast: {c}, Enhancement: {e}")
        return resp

    def set_tv_standard(self, ntsc: bool):
        """
        Set PAL/NTSC output:
        0: PAL, 1: NTSC.
        Command: 23 57 9E 01 00 [val] 00 45 4E 44
        """
        val = 1 if ntsc else 0
        cmd = self.HEADER_WRITE + bytes([0x9E, 0x01, 0x00, val, 0x00]) + self.FOOTER
        print(f"[N6Camera] Video standard set to {'NTSC' if ntsc else 'PAL'}")
        self.send_raw(cmd)
        return self.read_response()
