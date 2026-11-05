"""Startup must work in a new process, without test import-order side effects."""
import subprocess
import sys
import unittest
from pathlib import Path


class StartupImportsTests(unittest.TestCase):
    def test_main_imports_from_a_fresh_interpreter(self):
        result = subprocess.run([sys.executable, "-c", "import main; from app.ui.dialogs import WatchedImportDialog, CustomEntryDialog; print('imports-ok')"], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("imports-ok", result.stdout)
