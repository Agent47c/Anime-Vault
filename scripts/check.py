"""Shared local/CI validation. Run from any directory with Python 3.13."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["OFFLINE_MODE"] = "true"
    env["PYTHONUTF8"] = "1"
    commands = [
        [sys.executable, "-m", "compileall", "-q", "app", "scripts",
         *[p.name for p in ROOT.glob("*.py")]],
        [sys.executable, "scripts/run_tests.py"],
    ]
    with tempfile.TemporaryDirectory(prefix='animevault-validation-') as temporary:
        report=Path(temporary)/'completed.json'
        env['ANIMEVAULT_TEST_COMPLETION_FILE']=str(report)
        for command in commands:
            print("Running:", " ".join(command), flush=True)
            result = subprocess.run(command, cwd=ROOT, env=env)
            if result.returncode:
                return result.returncode
        try:completion=json.loads(report.read_text(encoding='utf-8'))
        except (OSError,ValueError):completion={}
        if not completion.get('successful') or not completion.get('expected') or completion.get('ran')!=completion.get('expected'):
            print('ERROR: Regression runner exited without confirming that every discovered test completed.',flush=True)
            return 1
    print("All checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
