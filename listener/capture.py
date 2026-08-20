"""Mic capture and system-wide push-to-talk hotkey."""

import collections
import threading

import numpy as np
import sounddevice as sd
from pynput import keyboard

from listener.config import AudioConfig

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


class Recorder:
    def __init__(self, cfg: AudioConfig, blocksize: int = 320) -> None:
        self.sample_rate = cfg.sample_rate
        self.channels = cfg.channels
        self.blocksize = blocksize
        preroll_blocks = max(
            1, int(cfg.sample_rate * cfg.preroll_ms / 1000 / blocksize)
        )
        self._preroll = collections.deque(maxlen=preroll_blocks)
        self._chunks: list[np.ndarray] = []
        self._recording = False
        self.level = 0.0
        self._lock = threading.Lock()
        self._stream = sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=cfg.channels,
            dtype="float32",
            blocksize=blocksize,
            callback=self._callback,
        )

    def _callback(self, indata, _frames, _time_info, _status) -> None:
        block = indata.copy()
        with self._lock:
            if self._recording:
                self._chunks.append(block)
                self.level = float(np.sqrt((block**2).mean()))
            else:
                self._preroll.append(block)

    def start_stream(self) -> None:
        self._stream.start()

    def start(self) -> None:
        """Begin recording; the pre-roll buffer is prepended so the first word isn't clipped."""
        with self._lock:
            self._chunks = list(self._preroll)
            self._preroll.clear()
            self._recording = True

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).flatten()

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


class PushToTalk:
    """Hold or toggle a key/chord. macOS does not expose the fn key to apps."""

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
