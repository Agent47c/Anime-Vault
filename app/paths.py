"""Separate immutable bundled resources from writable per-user installed data."""
import os
import sys
from pathlib import Path

RESOURCE_DIR = Path(__file__).resolve().parent.parent
FROZEN = bool(getattr(sys, 'frozen', False))


def data_directory(*, frozen=None, environ=None, source_root=None, home=None):
    frozen = FROZEN if frozen is None else frozen
    environ = os.environ if environ is None else environ
    override = environ.get('ANIMEVAULT_DATA_DIR')
    if override:
        path = Path(override)
        if not path.is_absolute():
            raise ValueError('ANIMEVAULT_DATA_DIR must be an absolute path.')
        return path
    if not frozen:
        return Path(source_root or RESOURCE_DIR) / 'data'
    local = environ.get('LOCALAPPDATA')
    base = Path(local) if local else Path(home or Path.home()) / 'AppData' / 'Local'
    if not base.is_absolute():
        raise ValueError('The Windows user-data folder must be an absolute path.')
    return base / 'AnimeVault'


DATA_DIR = data_directory()
CONFIG_FILE = (DATA_DIR if FROZEN else RESOURCE_DIR) / '.env'


def native_torrent_executable(executable=None):
    path = Path(executable or sys.executable).parent / 'engine' / 'AnimeVaultTorrentHost.exe'
    if not path.is_file():
        raise ValueError('The packaged download engine is missing. Reinstall Anime Vault; your library data is kept.')
    return path
