# Listener

Fully offline push-to-talk dictation on macOS. A dictation session captures an utterance, transcribes it, optionally cleans it, and injects the result at the cursor.

## Language

**Dictation session**:
One activation cycle: hotkey start, speak, hotkey stop, then transcribe → cleanup → inject.
_Avoid_: pipeline, flow, job

**Utterance**:
The audio captured between start and stop, including pre-roll.
_Avoid_: clip, recording (the audio blob), take

**Transcript**:
Raw speech-to-text output, before cleanup.
_Avoid_: caption, STT result

**Cleanup**:
Filler/punctuation/casing pass over a transcript. Short utterances skip it. Failure falls back to the transcript unchanged.
_Avoid_: rewrite, polish, LLM call

**Injection**:
Delivering cleaned text into the focused app (paste or type).
_Avoid_: paste (the method, not the act), send, insert

**Pre-roll**:
A short ring buffer of audio prepended when capture starts so the first word is not clipped.
_Avoid_: lookahead, buffer

**Hotkey**:
The configured key or chord that starts and stops a dictation session (hold or toggle).
_Avoid_: shortcut, trigger
