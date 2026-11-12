"""Worker-only player icon cache; prefer installed vendor artwork."""
import json,time,subprocess,os
from pathlib import Path
from app import db

SOURCES={'vlc':'https://www.videolan.org/favicon.ico','mpv':'https://mpv.io/favicon.ico','mpc-hc':'https://mpc-hc.org/favicon.ico','potplayer':'https://potplayer.daum.net/favicon.ico'}


def cached_icons():
    from app.config import detect_installed_players,get_custom_player_path
    from PyQt5.QtGui import QImage
    import requests
    root=Path(db.DATA_DIR)/'player-icons';root.mkdir(parents=True,exist_ok=True)
    manifest=root/'attempts.json'
    try:attempts=json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError,ValueError):attempts={}
    installed=detect_installed_players();custom=get_custom_player_path()
    if custom and Path(custom).is_file():installed['custom']=custom
    result={}
    for name in dict.fromkeys([*SOURCES,*installed]):
        path=root/(name+'.png')
        if path.is_file() and not QImage(str(path)).isNull():result[name]=str(path);continue
        if time.time()-attempts.get(name,0)<86400:continue
        attempts[name]=time.time()
        try:
            if name in installed and os.name=='nt' and (Path(__file__).resolve().parents[2]/'scripts'/'cache_player_icon.ps1').is_file():
                script=Path(__file__).resolve().parents[2]/'scripts'/'cache_player_icon.ps1'
                subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(script),installed[name],str(path)],creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,timeout=8,check=True)
            if not path.is_file() and name in SOURCES:
                with requests.get(SOURCES[name],timeout=(3,5),stream=True) as response:
                    response.raise_for_status();data=bytearray()
                    for block in response.iter_content(16384):
                        data.extend(block)
                        if len(data)>1024*1024:raise ValueError('Icon is too large')
                image=QImage.fromData(bytes(data))
                if not image.isNull():image.scaled(64,64).save(str(path),'PNG')
            if path.is_file() and not QImage(str(path)).isNull():result[name]=str(path)
        except (OSError,ValueError,subprocess.SubprocessError,requests.RequestException):pass
    manifest.write_text(json.dumps(attempts),encoding='utf-8')
    return result
