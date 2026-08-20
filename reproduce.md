# Run Listener on your MacBook

Listener is a fully offline dictation app for **macOS on Apple Silicon** (M1–M4).
Press `ctrl+shift` anywhere → speak → press again → clean text appears at your cursor.

```bash
brew install just          # one-time; skip if you already have it
just setup                 # Python env, llama.cpp, cleanup model
just run
```

That is the whole install. `just setup` skips anything already present.

Listener starts one `llama-server` child while it runs and stops it on quit. If you previously used Ollama, you can drop it:

```bash
brew services stop ollama   # if it was a login service
```

## Permissions (one time)

macOS will block the app until you allow it. In **System Settings → Privacy & Security**, add the Python binary printed at the end of `just setup` to:

- **Input Monitoring** — global hotkey
- **Accessibility** — paste into other apps
- **Microphone** — macOS asks on first recording; click Allow

The settings file picker hides dot-folders. Press `⌘⇧G` and paste the path, or run `open -R .venv/bin/python` and drag the file in. Restart after granting (`just run` again).

## Use it

Click into any text field (Notes, browser, Slack, anywhere):

1. Press `ctrl+shift` → a small waveform pill appears (recording)
2. Speak naturally — ums and uhs are fine, they get removed
3. Press `ctrl+shift` again → cleaned text is pasted at the cursor

## Optional recipes

```bash
just                  # list recipes
just run              # start in the foreground
just install-login    # start at every login (LaunchAgent)
just uninstall-login  # remove the login agent
```

Logs after `just install-login`: `tail -f ~/Library/Logs/listener.log`

## Customize (`config.yaml`, then restart)

- **Hotkey**: `hotkey.key` (e.g. `alt_r`, `ctrl+alt`) — `fn` is not possible on macOS
- **Hold vs toggle**: `hotkey.mode: hold | toggle`
- **LLM**: `llm.model` — Hugging Face GGUF (`repo:quant`) or a local `.gguf` path. Default is Qwen3-4B-Instruct (not the thinking variant).
- **Accuracy vs speed**: `stt.model: tiny.en | base | small | medium | large-v3`
