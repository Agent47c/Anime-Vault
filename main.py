"""
Anime Library & Storage Manager — Entry Point

Runs the PyQt5 desktop GUI and background FastAPI streaming server.
Run with:
    python main.py
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.startup import prepare_windowed_logging
prepare_windowed_logging()

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QLockFile

from app import db
from app import __version__
from app.config import get_theme
from app.ui.theme import apply_theme
from app.ui.main_window import MainWindow
from app.api import server


def main():
    # Elevation is opt-in and checked before starting the local server or GUI.
    if sys.platform == "win32" and db.DB_PATH.is_file():
        from app.config import get_always_admin
        import ctypes
        if get_always_admin() and not ctypes.windll.shell32.IsUserAnAdmin():
            from run_as_admin import launch
            try:
                launch()
            except Exception as error:
                ctypes.windll.user32.MessageBoxW(None, str(error), "Administrator launch", 0x10)
            return

    # 1. Enable High-DPI display scaling
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Anime Vault")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AnimeManager")

    db.DATA_DIR.mkdir(parents=True, exist_ok=True)
    instance_lock = QLockFile(str(db.DATA_DIR / "animevault.lock"))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock():
        QMessageBox.information(None, "Anime Vault", "Anime Vault is already open. Check the Windows system tray.")
        return

    db.init_db()
    server.start_server()

    # 5. Apply visual theme (dark by default)
    current_theme = get_theme()
    apply_theme(app, current_theme)

    # 6. Instantiate and display main window
    window = MainWindow()
    window.show()

    # 7. Ensure clean server shutdown on exit
    app.aboutToQuit.connect(server.stop_server)

    # 8. Start main GUI event loop
    exit_code = app.exec_()
    instance_lock.unlock()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
