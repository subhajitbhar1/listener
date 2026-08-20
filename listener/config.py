"""Typed app config loaded from config.yaml."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SttConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: Literal["faster-whisper", "mlx-whisper"] = "faster-whisper"
    model: str = "tiny.en"
    language: str | None = None
    compute_type: str = "int8"


class LlmConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    model: str
    host: str = "127.0.0.1"
    port: int = 8091
    n_gpu_layers: int = 99
    ctx_size: int = 2048
    temperature: float = 0.1
    min_words_for_cleanup: int = 10
    system_prompt: str


class HotkeyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    mode: Literal["hold", "toggle"] = "hold"


class AudioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_rate: int = 16000
    channels: int = 1
    preroll_ms: int = Field(default=500, ge=0)


class InjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["paste", "type"] = "paste"
    restore_clipboard: bool = True


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stt: SttConfig
    llm: LlmConfig
    hotkey: HotkeyConfig
    audio: AudioConfig
    inject: InjectConfig


def _config_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    cwd = Path.cwd() / "config.yaml"
    if cwd.exists():
        return cwd
    return Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: str | Path | None = None) -> AppConfig:
    with _config_path(path).open() as f:
        data = yaml.safe_load(f)
    return AppConfig.model_validate(data)
