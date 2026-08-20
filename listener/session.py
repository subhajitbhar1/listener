"""Dictation session: press/release owns capture, transcribe, cleanup, and inject."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from listener.capture import Recorder
from listener.cleanup import Cleaner
from listener.injection import inject
from listener.macos import Overlay
from listener.transcript import Transcriber

if TYPE_CHECKING:
    import numpy as np

    from listener.config import AppConfig

log = logging.getLogger(__name__)

CallOnMain = Callable[[Callable[[], None]], None]


class DictationSession:
    def __init__(self, cfg: AppConfig, call_on_main: CallOnMain) -> None:
        self.cfg = cfg
        self._call_on_main = call_on_main
        self.stt = Transcriber(cfg.stt)
        self.cleaner = Cleaner(cfg.llm)
        self.recorder = Recorder(cfg.audio)
        self.overlay = Overlay(lambda: self.recorder.level)

    def start_stream(self) -> None:
        self.recorder.start_stream()

    def press(self) -> None:
        self.recorder.start()
        self._call_on_main(self.overlay.show)

    def release(self) -> None:
        audio = self.recorder.stop()
        self._call_on_main(self.overlay.hide)
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio: np.ndarray) -> None:
        t0 = time.time()
        raw = self.stt.transcribe(audio)
        if not raw:
            log.info("no speech detected")
            return
        text = self.cleaner.clean(raw)
        inject(text, self.cfg.inject)
        log.info('→ "%s"  (%.2fs)', text, time.time() - t0)

    def close(self) -> None:
        self.recorder.close()
        self.cleaner.close()
