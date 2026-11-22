"""Restart Anime Vault after its current process releases files and mutexes."""
import os
import subprocess
import sys
from pathlib import Path


def restart_command():
    prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parents[1]/'main.py')]
    return prefix+['--restart-after',str(os.getpid())]+sys.argv[1:]


def schedule_restart():
    flags=0
    if os.name=='nt':flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(restart_command(),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,creationflags=flags,close_fds=True)


def wait_for_parent(pid):
    if pid<=0 or pid==os.getpid():raise ValueError('Invalid restart process')
    if os.name!='nt':raise RuntimeError('Restart handoff requires Windows')
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x00100000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return  # Parent has already exited.
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(handle,60000)!=0:raise RuntimeError('Previous Anime Vault process did not exit')
    finally:kernel.CloseHandle(handle)
