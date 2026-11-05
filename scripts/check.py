"""Shared local/CI validation. Run from any directory with Python 3.13."""
import os
from pathlib import Path
import subprocess
import sys


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
    for command in commands:
        print("Running:", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env)
        if result.returncode:
            return result.returncode
    print("All checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
