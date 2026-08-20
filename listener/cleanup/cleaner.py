"""
Transcript cleanup via llama.cpp. Model name comes ONLY from config.

Starts one `llama-server` child (brew: llama.cpp) for this app's lifetime.
"""

import atexit
import contextlib
import logging
import shutil
import subprocess
import time
from pathlib import Path

import requests

from listener.config import LlmConfig

log = logging.getLogger(__name__)


def _is_local_gguf(model: str) -> bool:
    return model.endswith(".gguf") or model.startswith(("/", "~"))


class Cleaner:
    def __init__(self, cfg: LlmConfig) -> None:
        self.cfg = cfg
        self.enabled = cfg.enabled
        self.base_url = f"http://{cfg.host}:{cfg.port}"
        self._proc: subprocess.Popen | None = None
        self._log_file = None
        if self.enabled and not self._ensure_server():
            self.enabled = False

    def _health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=2)
        except requests.RequestException:
            return False
        else:
            return r.ok

    def _server_cmd(self) -> list[str] | None:
        bin_path = shutil.which("llama-server")
        if not bin_path:
            return None
        cmd = [
            bin_path,
            "--host",
            self.cfg.host,
            "--port",
            str(self.cfg.port),
            "--no-webui",
            "-ngl",
            str(self.cfg.n_gpu_layers),
            "-c",
            str(self.cfg.ctx_size),
        ]
        if _is_local_gguf(self.cfg.model):
            cmd.extend(["-m", str(Path(self.cfg.model).expanduser())])
        else:
            cmd.extend(["-hf", self.cfg.model])
        return cmd

    def _ensure_server(self) -> bool:
        if self._health():
            return True
        cmd = self._server_cmd()
        if not cmd:
            log.warning("llama-server not found — run: brew install llama.cpp")
            log.warning("Falling back to raw transcripts (cleanup disabled).")
            return False
        log_path = Path.home() / "Library/Logs/listener-llamacpp.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log.info(
            "Starting llama.cpp (%s) — one process, logs: %s",
            self.cfg.model,
            log_path,
        )
        self._log_file = log_path.open("ab")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=self._log_file,
                stderr=self._log_file,
            )
        except OSError as e:
            log.warning("Failed to start llama-server (%s)", e)
            log.warning("Falling back to raw transcripts (cleanup disabled).")
            return False
        atexit.register(self.close)
        deadline = time.time() + 180
        while time.time() < deadline:
            if self._proc.poll() is not None:
                log.warning("llama-server exited during startup. Check %s", log_path)
                log.warning("Falling back to raw transcripts (cleanup disabled).")
                self.close()
                return False
            if self._health():
                return True
            time.sleep(0.4)
        log.warning(
            "llama-server did not become ready. Falling back to raw transcripts."
        )
        self.close()
        return False

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if self._log_file is not None:
            with contextlib.suppress(OSError):
                self._log_file.close()
            self._log_file = None

    def clean(self, text: str) -> str:
        if (
            not self.enabled
            or not text
            or len(text.split()) < self.cfg.min_words_for_cleanup
        ):
            return text
        try:
            r = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "system", "content": self.cfg.system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "temperature": self.cfg.temperature,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            r.raise_for_status()
            choices = r.json().get("choices") or []
            cleaned = (choices[0].get("message") or {}).get("content", "").strip()
        except requests.RequestException as e:
            log.warning("Cleanup failed (%s); using raw transcript.", e)
            return text
        else:
            return cleaned or text
