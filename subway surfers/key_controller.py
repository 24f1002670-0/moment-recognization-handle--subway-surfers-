"""
key_controller.py
------------------
Translates an abstract event ("LEFT", "JUMP", ...) into an actual OS-level
key press so the tracked movement controls a real game window.

Two backends supported:
  - pyautogui:     cross-platform (Windows/macOS/Linux), works for most apps.
  - pydirectinput: Windows-only, simulates DirectX-compatible input; use
                    this if pyautogui presses don't register in your game
                    (common with games built on DirectInput, e.g. many
                    Unity/old DirectX titles).

IMPORTANT: the game window must be focused/active for key presses to reach
it — this controller does not do window management.
"""

import time


class KeyController:
    def __init__(self, key_map, backend="pyautogui", enabled=True, press_seconds=0.05,
                 between_steps_seconds=0.12):
        self.key_map = key_map
        self.enabled = enabled
        self.press_seconds = press_seconds
        self._between_steps_seconds = between_steps_seconds
        self._backend_name = backend
        self._backend = None

        if enabled:
            if backend == "pydirectinput":
                import pydirectinput as backend_module
            else:
                import pyautogui as backend_module
                backend_module.PAUSE = 0  # don't let pyautogui sleep between calls
            self._backend = backend_module

    def fire(self, action):
        """action: 'left' | 'right' | 'jump' | 'duck' — single key press."""
        key = self.key_map.get(action)
        if key is None:
            print(f"[key_controller] '{action}' has no key bound in config.yaml — skipping")
            return
        if not self.enabled or self._backend is None:
            print(f"[key_controller] controller disabled — would have pressed '{key}' for '{action}'")
            return
        print(f"[key_controller] pressing '{key}' (backend={self._backend_name}) for action '{action}'")
        self._backend.keyDown(key)
        self._backend.keyUp(key)

    def fire_steps(self, direction, steps):
        """
        Presses the direction key `steps` times in a row, with a tiny gap
        between presses. Used for lane changes: most runner games shift
        one lane per press, so skipping 2 lanes needs 2 presses to keep
        the in-game lane in sync with your physical lane.
        """
        for i in range(steps):
            self.fire(direction)
            if i < steps - 1:
                time.sleep(self._between_steps_seconds)