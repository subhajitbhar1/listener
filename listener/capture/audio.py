"""Mic capture: continuous pre-roll ring buffer + on-demand recording."""

import collections
import threading

import numpy as np
import sounddevice as sd

from listener.config import AudioConfig


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
