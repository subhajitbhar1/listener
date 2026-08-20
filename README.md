# Listener

Fully offline voice dictation for macOS (Apple Silicon) — a free, local alternative to Wispr Flow.

Press `ctrl+shift` in any app → speak → press again → clean text appears at your cursor. Speech-to-text runs on-device (faster-whisper), filler removal and punctuation cleanup run through a local LLM (llama.cpp). No cloud, no subscription, no audio leaving your Mac.

- **Want to run it?** `brew install just && just setup && just run` — details in [reproduce.md](reproduce.md).
- **Want to build it yourself with AI?** [steps.md](steps.md) has the exact Claude Code prompts that created this app.

Built with Claude Code (planned with Opus 4.8, built with Fable 5).
