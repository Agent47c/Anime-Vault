"""Use Windows' recycle-only implementation; never fall back to legacy deletion."""
import sys


def send2trash(path):
    if sys.platform == 'win32':
        try:
            from send2trash.win.modern import send2trash as recycle
        except ImportError as error:
            raise OSError('Safe Recycle Bin support requires pywin32. File retained; repair the installation and retry.') from error
    else:
        from send2trash import send2trash as recycle
    recycle(path)
