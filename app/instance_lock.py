"""One desktop process per profile, including launches from the browser."""
import errno
import sys


def profile_instance_lock(directory):
    if sys.platform == 'win32':
        return WindowsProfileLock(directory / 'animevault.instance')

    from PyQt5.QtCore import QLockFile
    lock = QLockFile(str(directory / 'animevault.lock'))
    lock.setStaleLockTime(0)
    return lock


class WindowsProfileLock:
    """The open handle owns the lock. Copied files carry no lock state."""

    def __init__(self, path):
        self.path = path
        self._handle = None

    def tryLock(self):
        import msvcrt

        if self._handle is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open('a+b', buffering=0)
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            handle.close()
            if error.errno == errno.EACCES:
                return False
            raise
        self._handle = handle
        return True

    def unlock(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None
