"""macOS overlay, permissions, process name, and menu bar."""

import collections
import logging

import objc
import Quartz
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMenu,
    NSMenuItem,
    NSMutableParagraphStyle,
    NSPanel,
    NSParagraphStyleAttributeName,
    NSScreen,
    NSStatusBar,
    NSTimer,
    NSView,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from ApplicationServices import AXIsProcessTrusted
from Foundation import NSBundle, NSProcessInfo, NSString

log = logging.getLogger(__name__)

APP_NAME = "Listener"
BAR_COUNT = 24
PANEL_W, PANEL_H = 260, 74
LABEL_H = 20
_status_items: list = []


class WaveView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(WaveView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.levels = collections.deque([0.02] * BAR_COUNT, maxlen=BAR_COUNT)
        return self

    def drawRect_(self, _rect):
        b = self.bounds()
        NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.92).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(b, 16, 16).fill()
        pad, gap = 16, 3
        bw = (b.size.width - 2 * pad - gap * (BAR_COUNT - 1)) / BAR_COUNT
        wave_h = b.size.height - LABEL_H
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.64, 0.42, 1.0, 1.0).setFill()
        for i, lv in enumerate(self.levels):
            bh = max(4, min(1.0, lv * 10) * (wave_h - 18))
            x = pad + i * (bw + gap)
            y = LABEL_H + (wave_h - bh) / 2
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                ((x, y), (bw, bh)), bw / 2, bw / 2
            ).fill()
        style = NSMutableParagraphStyle.alloc().init()
        style.setAlignment_(1)  # center
        attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(11),
            NSForegroundColorAttributeName: NSColor.whiteColor(),
            NSParagraphStyleAttributeName: style,
        }
        NSString.stringWithString_("Listener").drawInRect_withAttributes_(
            ((0, 4), (b.size.width, 14)), attrs
        )


class Overlay:
    """show()/hide() must be called on the main thread (use AppHelper.callAfter)."""

    def __init__(self, level_fn):
        self.level_fn = level_fn
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - PANEL_W) / 2
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((x, 110), (PANEL_W, PANEL_H)),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setLevel_(25)  # above normal windows (status level)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setIgnoresMouseEvents_(True)
        self.panel.setCollectionBehavior_(1)  # visible on all Spaces
        self.view = WaveView.alloc().initWithFrame_(((0, 0), (PANEL_W, PANEL_H)))
        self.panel.setContentView_(self.view)
        self._timer = None

    def _tick(self, _timer):
        self.view.levels.append(self.level_fn())
        self.view.setNeedsDisplay_(True)

    def show(self):
        self.view.levels.extend([0.02] * BAR_COUNT)
        self.panel.orderFrontRegardless()
        self._timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            1 / 30.0, True, self._tick
        )

    def hide(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        self.panel.orderOut_(None)


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
