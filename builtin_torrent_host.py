"""Private stdio worker. No GUI imports, HTTP server or OS URL registration."""
import json
import os
import struct
import sys
from pathlib import Path

# AUDIT-START
if os.environ.get('APP_PROFILE') == '1':
    from app.audit_profile import bootstrap
    bootstrap()
# AUDIT-END


def binary_stream(name,mode,handle_id):
    stream=getattr(sys,name)
    if stream is not None:
        return stream.buffer
    # Windowed PyInstaller builds can leave sys.stdin/stdout as None even when
    # private pipe handles were inherited. Recreate only those worker streams.
    import ctypes
    from ctypes import wintypes
    import msvcrt
    get_handle=ctypes.windll.kernel32.GetStdHandle
    get_handle.argtypes=[wintypes.DWORD];get_handle.restype=wintypes.HANDLE
    handle=get_handle(handle_id)
    if not handle or handle==wintypes.HANDLE(-1).value:
        raise ValueError('Private worker pipe is unavailable.')
    descriptor=msvcrt.open_osfhandle(handle,os.O_BINARY | (os.O_RDONLY if mode=='rb' else os.O_WRONLY))
    return os.fdopen(descriptor,mode)


def run():
    incoming=binary_stream('stdin','rb',-10)
    outgoing=binary_stream('stdout','wb',-11)
    if os.name=='nt':
        import msvcrt
        msvcrt.setmode(incoming.fileno(),os.O_BINARY)
        msvcrt.setmode(outgoing.fileno(),os.O_BINARY)
    from app import db
    from app.core.builtin_torrents import Engine
    engine=None
    try:
        while True:
            raw=incoming.read(4)
            if len(raw)!=4: break
            size=struct.unpack('<I',raw)[0]
            if not 0<size<=32*1024*1024: break
            payload=incoming.read(size)
            if len(payload)!=size: break
            stop=False
            try:
                request=json.loads(payload)
                command=request['command'];value=None
                if command=='init' and engine is None:
                    db.DATA_DIR=Path(request['folder'])
                    engine=Engine(request['config'],network=request['network'])
                elif engine is None: raise ValueError('Engine is not initialized.')
                elif command=='configure': engine.configure(request['config'])
                elif command=='version': value=engine.lt.version
                elif command=='prepare':
                    item=request['item'];engine.prepare(item,request['source']);value=item
                elif command=='attach': engine.attach(request['item'])
                elif command=='snapshot': value=engine.snapshot(request['item'])
                elif command=='save': engine.save()
                elif command=='recheck': engine.recheck(request['item'])
                elif command=='close': engine.close();engine=None;stop=True
                else: raise ValueError('Unknown private engine command.')
                result={'value':value}
            except Exception as error:
                result={'error':str(error)}
            response=json.dumps(result).encode('utf-8')
            outgoing.write(struct.pack('<I',len(response))+response)
            outgoing.flush()
            if stop: break
    finally:
        if engine is not None: engine.close()
    return 0


if __name__=='__main__':
    raise SystemExit(run())
