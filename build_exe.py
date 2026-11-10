"""
Build script to compile Anime Library & Storage Manager into a standalone Windows .exe using PyInstaller.

Usage:
    pip install pyinstaller
    python build_exe.py
"""

import sys
import subprocess
from pathlib import Path


def build():
    base_dir = Path(__file__).resolve().parent
    main_script = base_dir / "main.py"

    print("=" * 60)
    print("Building AnimeManager.exe with PyInstaller...")
    print("=" * 60)

    try:
        import PyInstaller.__main__
    except ImportError:
        print("\n[!] PyInstaller is not installed. Installing now via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        import PyInstaller.__main__

    # Define build arguments
    args = [
        str(main_script),
        "--name=AnimeManager",
        "--onefile",
        "--windowed",  # Suppress terminal console window
        "--clean",
        "--noconfirm",
        # Hidden imports needed by FastAPI, Uvicorn, and dynamically loaded modules
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi",
        "--hidden-import=sqlite3",
        "--hidden-import=requests",
        "--collect-all=libtorrent",
        "--hidden-import=builtin_torrent_host",
        f"--add-data={base_dir / 'third_party' / 'libtorrent-LICENSE.txt'};third_party",
        "--hidden-import=PIL",
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
    ]

    print(f"Running PyInstaller with options: {' '.join(args)}")
    PyInstaller.__main__.run(args)
    print("\n[✓] Build complete! The executable is located in the 'dist/' folder.")


if __name__ == "__main__":
    build()
