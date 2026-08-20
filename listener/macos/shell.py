"""macOS app shell: permissions, process name, menu bar."""

import logging

import Quartz
from AppKit import NSMenu, NSMenuItem, NSStatusBar
from ApplicationServices import AXIsProcessTrusted
from Foundation import NSBundle, NSProcessInfo

log = logging.getLogger(__name__)

APP_NAME = "Listener"
_status_items: list = []


def check_permissions() -> None:
    msgs: list[str] = []
    try:
        if not Quartz.CGPreflightListenEventAccess():
            msgs.append("Input Monitoring (for the global hotkey)")
    except AttributeError:
        log.debug("Input Monitoring probe unavailable", exc_info=True)
    try:
        if not AXIsProcessTrusted():
            msgs.append("Accessibility (to paste text into other apps)")
    except Exception:
        log.debug("Accessibility probe failed", exc_info=True)
    if not msgs:
        return
    log.warning("SETUP NEEDED — grant these in System Settings → Privacy & Security:")
    for msg in msgs:
        log.warning("  - %s", msg)
    log.warning("  - Microphone (macOS will prompt on first recording)")


def rename_app() -> None:
    """Best-effort: show Listener instead of Python where macOS reads the bundle name."""
    try:
        NSProcessInfo.processInfo().setProcessName_(APP_NAME)
        info = NSBundle.mainBundle().infoDictionary()
        if info is not None:
            info["CFBundleName"] = APP_NAME
    except Exception:
        log.debug("Could not rename process", exc_info=True)


def install_status_item(hotkey: str) -> None:
    status = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
    status.button().setTitle_("🎙️")
    menu = NSMenu.alloc().init()
    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        f"{APP_NAME} — press {hotkey} to dictate",
        None,
        "",
    )
    item.setEnabled_(False)
    menu.addItem_(item)
    quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Quit " + APP_NAME,
        "terminate:",
        "q",
    )
    menu.addItem_(quit_item)
    status.setMenu_(menu)
    _status_items.append(status)
