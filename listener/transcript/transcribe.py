"""Local STT via faster-whisper (CTranslate2) with Silero VAD gating silence."""

import logging

import numpy as np
from faster_whisper import WhisperModel

from listener.config import SttConfig

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, cfg: SttConfig) -> None:
        self.cfg = cfg
        if cfg.engine == "mlx-whisper":
            import mlx_whisper  # noqa: PLC0415

            self._mlx = mlx_whisper
            self._model = None
        else:
            self._mlx = None
            log.info("loading faster-whisper model %s", cfg.model)
            self._model = WhisperModel(
                cfg.model,
                device="cpu",
                compute_type=cfg.compute_type,
            )

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        if self._mlx is not None:
            result = self._mlx.transcribe(audio, language=self.cfg.language)
            return result.get("text", "").strip()
        segments, _ = self._model.transcribe(
            audio,
            language=self.cfg.language,
            vad_filter=True,
            beam_size=1,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
