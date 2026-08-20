# Listener — macOS Apple Silicon
#
#   brew install just
#   just setup
#   just run

set shell := ["zsh", "-cu"]

export UV_PYTHON := "3.12"
root := justfile_directory()

# List recipes
default:
    @just --list

# One-shot Mac setup: uv, llama.cpp, Python deps, cleanup model
setup:
    #!/usr/bin/env zsh
    set -euo pipefail
    if [[ "$(uname -s)" != "Darwin" ]]; then
      print -u2 "This recipe is macOS-only."
      exit 1
    fi
    if [[ "$(uname -m)" != "arm64" ]]; then
      print -u2 "Listener targets Apple Silicon (M1–M4)."
      exit 1
    fi
    just _ensure-uv
    just _ensure-llamacpp
    just _sync
    just _pull-model
    print ""
    print "Setup complete. Next:"
    print "  1. just run"
    print "  2. Grant Microphone, Accessibility, and Input Monitoring"
    print "     (System Settings → Privacy & Security) to:"
    print "     $(just _python-bin)"

# Run Listener in the foreground
run:
    #!/usr/bin/env zsh
    if [[ ! -x "{{root}}/.venv/bin/python" ]]; then
      print -u2 "No venv yet. Run: just setup"
      exit 1
    fi
    cd "{{root}}" && uv run python -m listener

# Install a LaunchAgent so Listener starts at login
install-login: _sync
    #!/usr/bin/env zsh
    set -euo pipefail
    dest="$HOME/Library/LaunchAgents/com.subhajitbhar.listener.plist"
    mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
    python="$(just _python-bin)"
    "{{root}}/.venv/bin/python" -c 'import pathlib, plistlib, sys; dest, python, root, home = sys.argv[1:]; pathlib.Path(dest).write_bytes(plistlib.dumps({"Label": "com.subhajitbhar.listener", "ProgramArguments": [python, "-u", "-m", "listener"], "WorkingDirectory": root, "RunAtLoad": True, "KeepAlive": True, "StandardOutPath": home + "/Library/Logs/listener.log", "StandardErrorPath": home + "/Library/Logs/listener.log"}))' "$dest" "$python" "{{root}}" "$HOME"
    launchctl unload "$dest" 2>/dev/null || true
    launchctl load "$dest"
    print "Loaded $dest"
    print "Logs: tail -f ~/Library/Logs/listener.log"

# Remove the login LaunchAgent
uninstall-login:
    #!/usr/bin/env zsh
    dest="$HOME/Library/LaunchAgents/com.subhajitbhar.listener.plist"
    launchctl unload "$dest" 2>/dev/null || true
    rm -f "$dest"
    print "Removed login agent."

_python-bin:
    @"{{root}}/.venv/bin/python" -c "import os, sys; print(os.path.realpath(sys.executable))"

_ensure-uv:
    #!/usr/bin/env zsh
    set -euo pipefail
    if command -v uv >/dev/null; then
      exit 0
    fi
    if command -v brew >/dev/null; then
      brew install uv
    else
      print -u2 "Install Homebrew (https://brew.sh) or uv (https://docs.astral.sh/uv/), then re-run: just setup"
      exit 1
    fi

_ensure-llamacpp:
    #!/usr/bin/env zsh
    set -euo pipefail
    if command -v llama-server >/dev/null; then
      exit 0
    fi
    if command -v brew >/dev/null; then
      brew install llama.cpp
    else
      print -u2 "Install Homebrew (https://brew.sh), then re-run: just setup"
      exit 1
    fi

_sync:
    cd "{{root}}" && UV_RESOLUTION=highest uv venv --python "$UV_PYTHON" --allow-existing && UV_RESOLUTION=highest uv pip install .

_pull-model:
    #!/usr/bin/env zsh
    set -euo pipefail
    model="$(cd "{{root}}" && uv run python -c "from listener.config import load_config; print(load_config().llm.model)")"
    if [[ "$model" == *.gguf ]]; then
      local_path="${model/#\~/$HOME}"
      if [[ ! -f "$local_path" ]]; then
        print -u2 "GGUF not found: $local_path"
        exit 1
      fi
      print "Using local GGUF: $local_path"
      exit 0
    fi
    print "Caching llama.cpp model $model (~2.5 GB, one time)..."
    llama-cli -hf "$model" -n 1 -p "ok" --no-display-prompt -no-cnv --log-disable
