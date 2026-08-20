"""
Text injection at the cursor via clipboard paste or typed keystrokes.

Clipboard + synthesized Cmd+V (Quartz CGEvent), with a per-character Unicode
keystroke fallback. Saves and restores the clipboard.
"""

import time

import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString

from listener.config import InjectConfig

KEY_V = 9  # macOS virtual keycode for 'v'


def _set_clipboard(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)


def _get_clipboard() -> str | None:
    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_(NSPasteboardTypeString)


def _press_cmd_v() -> None:
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    down = Quartz.CGEventCreateKeyboardEvent(src, KEY_V, True)
    up = Quartz.CGEventCreateKeyboardEvent(src, KEY_V, False)
    Quartz.CGEventSetFlags(down, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventSetFlags(up, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def _type_unicode(text: str) -> None:
    """Fallback: per-character CGEvent Unicode keystrokes (no clipboard involved)."""
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for ch in text:
        down = Quartz.CGEventCreateKeyboardEvent(src, 0, True)
        Quartz.CGEventKeyboardSetUnicodeString(down, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
        up = Quartz.CGEventCreateKeyboardEvent(src, 0, False)
        Quartz.CGEventKeyboardSetUnicodeString(up, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
        time.sleep(0.002)


def inject(text: str, cfg: InjectConfig) -> None:
    if not text:
        return
    if cfg.method == "type":
        _type_unicode(text)
        return
    old = _get_clipboard() if cfg.restore_clipboard else None
    _set_clipboard(text)
    time.sleep(0.05)  # let the pasteboard settle
    _press_cmd_v()
    if old is not None:
        time.sleep(0.25)  # let the paste land before restoring
        _set_clipboard(old)
