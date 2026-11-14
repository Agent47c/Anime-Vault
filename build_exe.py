"""Build an isolated-data Windows application and optional Inno Setup installer.

Install requirements-build.txt first, then:
    python build_exe.py --installer --iscc "C:/path/to/ISCC.exe"
The payload uses an explicit resource allowlist; user data is never bundled.
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify_payload(bundle):
    prohibited = []
    for path in bundle.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle)
        # Requests needs this public TLS trust bundle. It is not a private key.
        if relative.parts[-3:] == ('_internal', 'certifi', 'cacert.pem') and b'PRIVATE KEY' not in path.read_bytes():
            continue
        if path.name == '.env' or path.suffix.lower() in ('.db', '.sqlite', '.sqlite3', '.pem', '.key', '.fastresume', '.torrent', '.mkv', '.mp4'):
            prohibited.append(str(relative))
    if prohibited:
        raise RuntimeError('Private/runtime files unexpectedly entered the payload: '+repr(prohibited))


def make_icon():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from io import BytesIO
    from PIL import Image
    target = ROOT / 'assets' / 'app.ico'
    master_png = ROOT / 'design' / 'references' / 'Anime Valt Installer Pkg' / 'Master App Icon.png'
    if master_png.is_file():
        im = Image.open(master_png)
        target.parent.mkdir(parents=True, exist_ok=True)
        im.save(target, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
        return target
    from PyQt5.QtCore import Qt, QBuffer, QIODevice
    from PyQt5.QtGui import QPixmap, QPainter, QColor
    from PyQt5.QtWidgets import QApplication
    from app.ui.icons import icon
    app = QApplication.instance() or QApplication([])
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#14121d'))
    painter.drawRoundedRect(0, 0, 256, 256, 52, 52)
    painter.drawPixmap(32, 32, icon('flower', '#ff6584').pixmap(192, 192))
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, 'PNG')
    target = ROOT / 'assets' / 'app.ico'
    Image.open(BytesIO(bytes(buffer.data()))).save(target, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return target


def build():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', action='store_true')
    parser.add_argument('--iscc', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        parser.error('Build with 64-bit Python on Windows.')
    try:
        import PyInstaller.__main__
    except ImportError:
        parser.error('Install requirements-build.txt in an isolated build environment first.')
    from app import __version__
    app_icon = make_icon()
    work = ROOT / 'build' / 'pyinstaller'
    work.mkdir(parents=True, exist_ok=True)
    version_file = work / 'version.txt'
    numbers = tuple(int(v) for v in __version__.split('.')[:3]) + (0,)
    version_file.write_text(
        'VSVersionInfo(ffi=FixedFileInfo(filevers='+repr(numbers)+',prodvers='+repr(numbers)+',mask=0x3f,flags=0,OS=0x40004,fileType=0x1,subtype=0,date=(0,0)),kids=['
        'StringFileInfo([StringTable("040904B0",['
        'StringStruct("CompanyName","Agent47c"),StringStruct("FileDescription","Anime Vault desktop library manager"),'
        'StringStruct("ProductName","Anime Vault"),StringStruct("OriginalFilename","AnimeVault.exe"),'
        'StringStruct("FileVersion","'+__version__+'"),StringStruct("ProductVersion","'+__version__+'")])]),'
        'VarFileInfo([VarStruct("Translation",[1033,1200])])])', encoding='utf-8')
    options = [str(ROOT/'main.py'), '--name=AnimeVault', '--onedir', '--windowed', '--clean', '--noconfirm',
               '--distpath='+str(ROOT/'dist'), '--workpath='+str(work), '--specpath='+str(work),
               '--icon='+str(app_icon), '--version-file='+str(version_file),
               '--collect-submodules=app', '--exclude-module=libtorrent']
    hidden = ['builtin_torrent_host', 'run_as_admin', 'uvicorn.logging', 'uvicorn.loops.auto',
              'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on',
              'PyQt5.QtSvg', 'PyQt5.QtNetwork', 'win32crypt', 'win32api', 'pythoncom', 'pywintypes']
    options.extend('--hidden-import='+name for name in hidden)
    resources = [('assets/fonts', 'assets/fonts'), ('app/ui/assets', 'app/ui/assets'),
                 ('third_party', 'third_party'), ('browser-extension', 'browser-extension'),
                 ('scripts/cache_player_icon.ps1', 'scripts'), ('docs/INSTALLER_GUIDE.md', 'docs')]
    for source, destination in resources:
        options.append('--add-data='+str(ROOT/source)+os.pathsep+destination)
    PyInstaller.__main__.run(options)
    bundle = ROOT/'dist'/'AnimeVault'
    native_work = work/'native'
    native_work.mkdir(parents=True,exist_ok=True)
    PyInstaller.__main__.run([str(ROOT/'builtin_torrent_host.py'), '--name=AnimeVaultTorrentHost',
                             '--onedir', '--console', '--clean', '--noconfirm',
                             '--exclude-module=PyQt5', '--collect-all=libtorrent',
                             '--distpath='+str(work/'native-output'), '--workpath='+str(native_work),
                             '--specpath='+str(native_work), '--icon='+str(app_icon),
                             '--version-file='+str(version_file)])
    shutil.copytree(work/'native-output'/'AnimeVaultTorrentHost', bundle/'engine', dirs_exist_ok=True)
    if list((bundle/'engine').rglob('Qt5Core.dll')):
        raise RuntimeError('Qt must not be bundled in the isolated native engine.')
    verify_payload(bundle)
    if args.installer:
        compiler = args.iscc or (Path(shutil.which('ISCC.exe')) if shutil.which('ISCC.exe') else None)
        if not compiler or not compiler.is_file():
            parser.error('Pass --iscc pointing to the installed Inno Setup compiler.')
        subprocess.run([str(compiler), '/DAppVersion='+__version__, str(ROOT/'installer'/'AnimeVault.iss')], check=True)
        setup = ROOT/'dist'/'installer'/f'AnimeVault-Setup-{__version__}-windows-x64.exe'
        digest = hashlib.sha256(setup.read_bytes()).hexdigest()
        setup.with_suffix('.exe.sha256').write_text(digest+'  '+setup.name+'\n', encoding='ascii')
        print(json.dumps({'installer':str(setup), 'bytes':setup.stat().st_size, 'sha256':digest}, indent=2))
    print('Standalone payload:', bundle)


if __name__ == '__main__':
    build()
