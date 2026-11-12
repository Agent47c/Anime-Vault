# AUDIT-START
"""Read-only library counts and installed versions. No filenames/title contents."""
import os
os.environ['APP_PROFILE']='1'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.audit_profile import bootstrap,emit,_original_connect
bootstrap()
import importlib.metadata
import json
import sqlite3
import time
from app import db


def main():
    versions={}
    for package in ('PyQt5','PyQt5-Qt5','requests','fastapi','uvicorn','Pillow','Send2Trash','libtorrent','pywin32'):
        try:versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:versions[package]='Not installed as distribution'
    versions['python']=sys.version.split()[0];versions['sqlite']=sqlite3.sqlite_version
    started=time.perf_counter();result={'versions':versions,'tables':{},'indexes':[]}
    if db.DB_PATH.is_file():
        conn=_original_connect(db.DB_PATH.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            conn.execute('PRAGMA query_only=ON')
            tables=[row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                escaped=table.replace('"','""')
                result['tables'][table]=conn.execute(f'SELECT count(*) FROM "{escaped}"').fetchone()[0]
            result['indexes']=[dict(name=row[0],table=row[1],sql=row[2]) for row in conn.execute("SELECT name,tbl_name,sql FROM sqlite_master WHERE type='index'")]
            result['journal_mode']=conn.execute('PRAGMA journal_mode').fetchone()[0]
            result['db_bytes']=db.DB_PATH.stat().st_size
            result['stored_video_names']=sum(len(json.loads(row[0] or '[]')) for row in conn.execute('SELECT video_files_json FROM seasons'))
        finally:conn.close()
    emit('audit.read_only_inventory',(time.perf_counter()-started)*1000,**result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
# AUDIT-END
