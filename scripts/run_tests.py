"""Run regression tests with a fresh, temporary application data directory."""
import gc
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OFFLINE_MODE"] = "true"


def main():
    from app import db, config

    # Theme initialization reads saved preferences before per-test fixtures run.
    # Give it an initialized baseline without accessing the user's real database.
    with tempfile.TemporaryDirectory(prefix="animevault-tests-") as temporary:
        root = Path(temporary)
        with ExitStack() as stack:
            for module in (db, config):
                for key, value in {
                    "DATA_DIR": root,
                    "COVERS_DIR": root / "covers",
                    "EXPORTS_DIR": root / "exports",
                }.items():
                    stack.enter_context(patch.object(module, key, value))
            stack.enter_context(patch.object(db, "DB_PATH", root / "library.db"))
            db.init_db()
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QCoreApplication, QEvent
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            gc.collect()
            return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
