"""Run regression tests with a fresh, temporary application data directory."""
import gc
import json
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
    # Theme initialization reads saved preferences before per-test fixtures run.
    # Give it an initialized baseline without accessing the user's real database.
    with tempfile.TemporaryDirectory(prefix="animevault-tests-") as temporary:
        root = Path(temporary)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {'ANIMEVAULT_DATA_DIR': str(root)}))
            from app import db, config

            for module in (db, config):
                for key, value in {
                    "DATA_DIR": root,
                    "COVERS_DIR": root / "covers",
                    "EXPORTS_DIR": root / "exports",
                }.items():
                    stack.enter_context(patch.object(module, key, value))
            stack.enter_context(patch.object(db, "DB_PATH", root / "library.db"))
            db.init_db()
            loader = unittest.TestLoader()
            tests_dir = str(ROOT / 'tests')
            if sys.argv[1:]:
                sys.path.insert(0, tests_dir)
                stack.callback(sys.path.remove, tests_dir)
                suite = loader.loadTestsFromNames(sys.argv[1:])
            else:
                suite = loader.discover(tests_dir)
            expected = suite.countTestCases()
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QCoreApplication, QEvent
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            gc.collect()
            completion = os.environ.get('ANIMEVAULT_TEST_COMPLETION_FILE')
            if completion:
                Path(completion).write_text(json.dumps({'expected':expected,'ran':result.testsRun,'successful':result.wasSuccessful()}),encoding='utf-8')
            return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
