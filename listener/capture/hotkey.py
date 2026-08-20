"""
System-wide push-to-talk hotkey via pynput.

Supports a single key ("alt_r") or a chord ("ctrl+alt"), and two modes:
  hold   — record while the keys are held, stop on release
  toggle — press the chord once to start, press it again to stop
Note: macOS does not expose the fn key to apps, so fn can't be used.
"""

from pynput import keyboard

KEY_MAP = {
    "alt": keyboard.Key.alt,  # left Option
    "alt_r": keyboard.Key.alt_r,  # right Option
    "ctrl": keyboard.Key.ctrl,
    "ctrl_r": keyboard.Key.ctrl_r,
    "cmd": keyboard.Key.cmd,
    "cmd_r": keyboard.Key.cmd_r,
    "shift": keyboard.Key.shift,
    "f13": keyboard.Key.f13,
}


class PushToTalk:
    def __init__(self, key_name, on_press, on_release, mode="hold"):
        names = [n.strip() for n in key_name.split("+")]
        unknown = [n for n in names if n not in KEY_MAP]
        if unknown:
            msg = f"Unknown hotkey(s) {unknown}. Choose from: {list(KEY_MAP)}"
            raise ValueError(msg)
        self.chord = {KEY_MAP[n] for n in names}
        self.mode = mode
        self.on_press_cb = on_press
        self.on_release_cb = on_release
        self._down = set()
        self._chord_held = False  # chord physically complete right now
        self._recording = False  # logical recording state (drives toggle mode)
        self._listener = keyboard.Listener(
            on_press=self._press, on_release=self._release
        )

    def _press(self, key):
        if key not in self.chord:
            return
        self._down.add(key)
        if self._chord_held or self._down != self.chord:
            return
        self._chord_held = True
        if self.mode == "toggle" and self._recording:
            self._recording = False
            self.on_release_cb()
            return
        self._recording = True
        self.on_press_cb()

    def _release(self, key):
        if key not in self.chord:
            return
        self._down.discard(key)
        if not self._chord_held or self._down == self.chord:
            return
        self._chord_held = False
        if self.mode == "hold" and self._recording:
            self._recording = False
            self.on_release_cb()

    def start(self):
        """Non-blocking; the AppKit run loop owns the process."""
        self._listener.start()
