"""Application bootstrap for ALPHA Typing Assistant."""
from __future__ import annotations

import atexit
import sys
import tkinter as tk

from . import airgap
from .dashboard import DashboardUI
from .engine import GlobalAssistant
from .logging_setup import get_logger, setup_logging
from .settings import Settings
from .store import BackgroundWriter, DataManager
from .ui_queue import UIDispatcher

log = get_logger("main")


def main(argv=None) -> int:
    """Start the dashboard and the global keyboard hook."""
    setup_logging()
    airgap.install()

    writer = BackgroundWriter()
    atexit.register(writer.shutdown)

    root = tk.Tk()
    dispatcher = UIDispatcher(root)

    dm = DataManager(writer)
    settings = Settings()
    assistant = GlobalAssistant(root, dispatcher, dm=dm, settings=settings)
    DashboardUI(root, assistant)

    dispatcher.start()
    root.after(100, assistant.start)

    def shutdown():
        try:
            assistant.stop()
            writer.flush()
        finally:
            writer.shutdown()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", shutdown)

    log.info("=" * 55)
    log.info(" ALPHA Typing Assistant v6.0 - active & ready")
    log.info(" - type 2+ letters      : suggestions popup appears")
    log.info(" - press Space          : auto-correct typos")
    log.info(" - double Ctrl/Ctrl+Space: open the popup manually")
    log.info(" - Up/Down + Enter      : pick a suggestion")
    log.info(" - Ctrl+Alt+X           : toggle assistant")
    log.info(" - Ctrl+Alt+S           : session summary")
    log.info("=" * 55)

    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
