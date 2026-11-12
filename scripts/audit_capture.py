# AUDIT-START
"""Read external Python/native stacks into the existing audit JSONL log.

Requires the locally installed audit_logs/tools/bin/py-spy.exe. Never requests
locals or a memory dump; --native briefly pauses for a consistent stack sample.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ['APP_PROFILE']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.audit_profile import bootstrap,emit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pid',required=True,type=int)
    parser.add_argument('--native',action='store_true');args=parser.parse_args()
    bootstrap()
    tool=Path(__file__).resolve().parents[1]/'audit_logs'/'tools'/'bin'/'py-spy.exe'
    command=[str(tool),'dump','--pid',str(args.pid),'--json','--full-filenames']
    command+=['--native'] if args.native else ['--nonblocking']
    started=time.perf_counter()
    result=subprocess.run(command,check=True,capture_output=True,text=True,timeout=30)
    stacks=[]
    for thread in json.loads(result.stdout):
        stacks.append(dict(thread_id=thread.get('thread_id'),thread=thread.get('thread_name'),
                           owns_gil=thread.get('owns_gil'),
                           frames=[dict(function=frame['name'],file=frame['filename'],line=frame['line']) for frame in thread['frames']]))
    emit('audit.external_stack',(time.perf_counter()-started)*1000,len(stacks),
         target_pid=args.pid,native=args.native,stacks=stacks,tool='py-spy 0.4.3',
         capture='function locations only; no locals or raw process memory saved')
    for thread in stacks:
        frames=thread['frames']
        if thread['thread']=='MainThread' or thread['owns_gil']:
            print(json.dumps(thread,indent=2))


if __name__=='__main__':main()
# AUDIT-END
