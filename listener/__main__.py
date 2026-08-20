"""Listener: press the hotkey anywhere to dictate. Fully offline."""

import logging

from AppKit import NSApplication
from PyObjCTools import AppHelper

from listener.capture import PushToTalk
from listener.config import load_config
from listener.macos import APP_NAME, check_permissions, install_status_item, rename_app
from listener.session import DictationSession

log = logging.getLogger("listener")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    cfg = load_config()
    check_permissions()

    rename_app()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)  # accessory: no Dock icon
    install_status_item(cfg.hotkey.key)

    log.info("Loading STT model (%s)...", cfg.stt.model)
    session = DictationSession(cfg, AppHelper.callAfter)
    session.start_stream()

    PushToTalk(
        cfg.hotkey.key,
        session.press,
        session.release,
        mode=cfg.hotkey.mode,
    ).start()
    action = "Press" if cfg.hotkey.mode == "toggle" else "Hold"
    log.info(
        "%s ready. %s [%s] to dictate (%s mode).",
        APP_NAME,
        action,
        cfg.hotkey.key,
        cfg.hotkey.mode,
    )
    try:
        AppHelper.runEventLoop()
    finally:
        session.close()


if __name__ == "__main__":
    main()
