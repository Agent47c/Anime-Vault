"""Selected-site Chrome native-messaging host. Never registers a URL protocol."""
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path
from app import db
from app.core import downloads
from app.core.magnet_capture import validate,enqueue

HOST='com.animevault.capture'
ROOT=Path(__file__).resolve().parents[2]


def origin(url):
    from urllib.parse import urlsplit
    value=urlsplit(url)
    if value.scheme not in ('http','https') or not value.hostname or '*' in value.hostname or value.username or value.password:
        raise ValueError('Choose an http/https search website without URL credentials.')
    port=value.port
    host=value.hostname.lower()
    if ':' in host: host='['+host+']'
    suffix=':'+str(port) if port and port!={'http':80,'https':443}[value.scheme] else ''
    return value.scheme+'://'+host+suffix


def register(extension_id):
    if sys.platform!='win32': raise ValueError('The Chrome bridge currently supports Windows.')
    if not re.fullmatch('[a-p]{32}',extension_id):
        raise ValueError('Paste the 32-character extension ID shown at chrome://extensions.')
    directory=db.DATA_DIR/'chrome-bridge'
    directory.mkdir(parents=True,exist_ok=True)
    launcher=directory/'host.cmd'
    if getattr(sys,'frozen',False):
        args=[sys.executable,'--native-magnet-host']
    else:
        args=[sys.executable,str(ROOT/'chrome_magnet_host.py')]
    # Only fixed local launcher paths and Chrome's extension-origin arguments
    # enter cmd.exe. Magnet/site data travels exclusively in framed stdin JSON.
    quoted=[]
    for arg in args:
        if any(c in arg for c in '\r\n"'): raise ValueError('The launcher path cannot contain quotes or line breaks.')
        quoted.append('"'+arg.replace('%','%%')+'"')
    launcher.write_text('@echo off\nchcp 65001 >nul\n'+ ' '.join(quoted)+' %*\n',encoding='utf-8')
    manifest={'name':HOST,'description':'Anime Vault selected-site magnet bridge','path':str(launcher.resolve()),
              'type':'stdio','allowed_origins':['chrome-extension://'+extension_id+'/']}
    path=directory/'host.json'
    path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    import winreg
    keypath='Software\\Google\\Chrome\\NativeMessagingHosts\\'+HOST
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,keypath,0,winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key,'',0,winreg.REG_SZ,str(path.resolve()))
    db.set_state('chrome.capture_extension',extension_id)
    return 'Chrome bridge connected. Enable capture for the same website in the extension popup.'


def validate_caller(caller):
    extension_id=db.get_state('chrome.capture_extension','')
    if not re.fullmatch('[a-p]{32}',extension_id) or caller.rstrip('/')!='chrome-extension://'+extension_id:
        raise ValueError('This Chrome extension is not connected to Anime Vault.')


def accept_message(message,caller):
    validate_caller(caller)
    if not isinstance(message,dict) or message.get('action')!='capture':
        raise ValueError('Unsupported browser message.')
    from app.core.download_discovery import sources
    allowed={origin(row['url']) for row in sources()}
    site=message.get('site')
    if not isinstance(site,str) or origin(site) not in allowed:
        raise ValueError('This website is not the selected download source in Anime Vault.')
    uri=message.get('magnet')
    validate(uri)
    return enqueue(uri)


def _read_exact(stream,length):
    chunks=[]
    while length:
        part=stream.read(length)
        if not part: raise ValueError('Incomplete native message.')
        chunks.append(part);length-=len(part)
    return b''.join(chunks)


def read_message(stream):
    length=struct.unpack('<I',_read_exact(stream,4))[0]
    if not 0<length<=65536: raise ValueError('Native message exceeds the size limit.')
    return json.loads(_read_exact(stream,length).decode('utf-8'))


def write_message(stream,value):
    encoded=json.dumps(value).encode('utf-8')
    stream.write(struct.pack('<I',len(encoded))+encoded);stream.flush()


def launch_desktop():
    from PyQt5.QtCore import QCoreApplication,QLockFile
    app=QCoreApplication.instance() or QCoreApplication([])
    lock=QLockFile(str(db.DATA_DIR/'animevault.lock'));lock.setStaleLockTime(0)
    if not lock.tryLock(): return
    lock.unlock()
    if getattr(sys,'frozen',False): args=[sys.executable,'--from-browser']
    else:
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        args=[str(pythonw if pythonw.exists() else Path(sys.executable)),str(ROOT/'main.py'),'--from-browser']
    subprocess.Popen(args,cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def run(args=None,stdin=None,stdout=None):
    if sys.platform=='win32' and stdin is None:
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    source=stdin or sys.stdin.buffer;target=stdout or sys.stdout.buffer
    try:
        caller=(sys.argv[1:] if args is None else args)[0]
        message=read_message(source)
        if isinstance(message,dict) and message.get('action')=='connect':
            validate_caller(caller)
            return connected_loop(message,caller,source,target)
        identifier=accept_message(message,caller)
        launch_desktop()
        write_message(target,{'ok':True,'id':identifier})
        return 0
    except Exception:
        # Do not echo magnet tracker URLs, local credentials or raw browser data.
        write_message(target,{'ok':False,'error':'Capture failed. Check the connected extension ID and selected source website in Anime Vault.'})
        return 1


def connected_loop(initial,caller,source,target):
    import queue,threading,time
    from app.core import source_bridge
    received=queue.Queue()
    def read():
        try:
            while True: received.put(read_message(source))
        except Exception: received.put(None)
    reader=threading.Thread(target=read,daemon=True);reader.start()
    message=initial;seen=0;site='';enabled=False
    try:
        while True:
            validate_caller(caller)
            if message is not None:
                action=message.get('action')
                if action in ('connect','heartbeat'):
                    site=origin(message.get('site',''));enabled=message.get('enabled') is True
                elif action=='search_result':
                    try: source_bridge.finish(message.get('id'),site,message.get('results'),message.get('error'))
                    except ValueError: pass  # A cancelled/expired search must not drop the bridge.
                message=None
            if time.monotonic()-seen>=4:
                source_bridge.heartbeat(site,enabled);seen=time.monotonic()
                write_message(target,{'action':'connected','site':site})
            if enabled:
                command=source_bridge.claim(site)
                if command: write_message(target,{'action':'search','id':command['id'],'url':command['url']})
            try:
                message=received.get(timeout=.3)
                if message is None: return 0
            except queue.Empty: pass
    finally:
        source_bridge.heartbeat(site,False)
