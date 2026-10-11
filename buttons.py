"""
Hardware Button and Switch Debouncer for MicroPython.
Supports debouncing, short click, and long press events.
"""

import machine
import time

class Button:
    def __init__(self, pin_num: int, name="Button", active_low=True, debounce_ms=35, long_press_ms=800):
        self.pin_num = pin_num
        self.name = name
        self.active_low = active_low
        self.debounce_ms = debounce_ms
        self.long_press_ms = long_press_ms

        pull = machine.Pin.PULL_UP if active_low else machine.Pin.PULL_DOWN
        self.pin = machine.Pin(pin_num, machine.Pin.IN, pull)

        self.last_raw_state = self._read_is_pressed()
        self.steady_state = self.last_raw_state
        self.last_debounce_time = time.ticks_ms()
        self.press_start_time = 0
        self.long_press_triggered = False

        # Callbacks
        self.on_click = None        # def callback(btn)
        self.on_long_press = None   # def callback(btn)
        self.on_press = None        # def callback(btn)
        self.on_release = None      # def callback(btn)

    def _read_is_pressed(self) -> bool:
        val = self.pin.value()
        return (val == 0) if self.active_low else (val == 1)

    def is_pressed(self) -> bool:
        return self.steady_state

    def update(self, now_ms=None):
        if now_ms is None:
            now_ms = time.ticks_ms()

        raw_state = self._read_is_pressed()

        # If raw reading changed, reset debounce timer
        if raw_state != self.last_raw_state:
            self.last_debounce_time = now_ms
            self.last_raw_state = raw_state

        # Check if reading has been steady for debounce duration
        if time.ticks_diff(now_ms, self.last_debounce_time) >= self.debounce_ms:
            if raw_state != self.steady_state:
                self.steady_state = raw_state

                if self.steady_state:
                    # Transition: Released -> Pressed
                    self.press_start_time = now_ms
                    self.long_press_triggered = False
                    if self.on_press:
                        self.on_press(self)
                else:
                    # Transition: Pressed -> Released
                    press_duration = time.ticks_diff(now_ms, self.press_start_time)
                    if self.on_release:
                        self.on_release(self)

                    # If long press wasn't already triggered, trigger short click
                    if not self.long_press_triggered:
                        if self.on_click:
                            self.on_click(self)

        # Check for long press while button is held
        if self.steady_state and not self.long_press_triggered:
            if time.ticks_diff(now_ms, self.press_start_time) >= self.long_press_ms:
                self.long_press_triggered = True
                if self.on_long_press:
                    self.on_long_press(self)
