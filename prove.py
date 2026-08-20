"""One end-to-end proof run: wav -> STT -> llama.cpp cleanup -> clipboard round-trip."""

import logging
import sys
import time
import wave

import numpy as np

from listener.cleanup import Cleaner
from listener.config import load_config
from listener.injection.inject import _get_clipboard, _set_clipboard
from listener.transcript import Transcriber

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("prove")

cfg = load_config()

with wave.open(sys.argv[1]) as w:
    assert (
        w.getframerate() == cfg.audio.sample_rate
        and w.getnchannels() == cfg.audio.channels
    )
    audio = (
        np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )
log.info("[1/4] audio loaded: %.1fs", len(audio) / cfg.audio.sample_rate)

t0 = time.time()
stt = Transcriber(cfg.stt)
raw = stt.transcribe(audio)
log.info('[2/4] STT (%.2fs incl. model load): "%s"', time.time() - t0, raw)

t0 = time.time()
cleaner = Cleaner(cfg.llm)
cleaned = cleaner.clean(raw)
log.info('[3/4] cleanup via %s (%.2fs): "%s"', cfg.llm.model, time.time() - t0, cleaned)
cleaner.close()

before = _get_clipboard()
_set_clipboard(cleaned)
assert _get_clipboard() == cleaned
if before is not None:
    _set_clipboard(before)
    assert _get_clipboard() == before
log.info("[4/4] clipboard injection round-trip OK (original clipboard restored)")
