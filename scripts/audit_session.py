# AUDIT-START
"""Summarize local JSONL evidence without printing payloads or stack contents."""
import argparse
import collections
import json
from pathlib import Path
import statistics

LOG=Path(__file__).resolve().parents[1]/'audit_logs'/'profile.jsonl'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--session',help='Limit to one session ID; otherwise all sessions')
    args=parser.parse_args();groups=collections.defaultdict(list);sessions={};bad=0
    if not LOG.is_file():print('No profiling log yet.');return
    with LOG.open(encoding='utf-8') as stream:
        for line in stream:
            try:row=json.loads(line)
            except ValueError:bad+=1;continue
            session=sessions.setdefault(row['session'],dict(pid=row['pid'],fixture=False,gui=False,ended=False))
            if row.get('fixture') or row['action'].startswith('audit.smoke'):session['fixture']=True
            if row['action']=='startup.QApplication':session['gui']=True
            if row['action']=='audit.session_end':session['ended']=True
    chosen=args.session
    if not chosen:
        candidates=[key for key,value in sessions.items() if value['gui'] and not value['fixture']]
        if not candidates:candidates=[key for key,value in sessions.items() if value['gui'] and value['ended']]
        if candidates:chosen=candidates[-1]
    if chosen not in sessions:
        print('No matching GUI session yet. Launch the app with APP_PROFILE=1.');return
    with LOG.open(encoding='utf-8') as stream:
        for line in stream:
            try:row=json.loads(line)
            except ValueError:continue
            if row['session']==chosen:groups[row['action']].append(row)
    print('Selected session:',chosen,json.dumps(sessions[chosen]));print('Malformed records across file:',bad)
    if sessions[chosen]['fixture']:print('VERIFICATION FIXTURE ONLY: not a real-library performance benchmark.')
    if not sessions[chosen]['ended']:print('Session is still running or ended abruptly; final records may be pending.')
    print('Durations are inclusive wall time; do not sum nested actions.')
    for action,rows in sorted(groups.items(),key=lambda item:max(row.get('duration_ms',0) for row in item[1]),reverse=True)[:45]:
        values=sorted(row.get('duration_ms',0) for row in rows)
        p95=values[max(0,__import__('math').ceil(len(values)*.95)-1)]
        print(f'{action}: n={len(rows)}, median={statistics.median(values):.3f} ms, p95={p95:.3f} ms, max={max(values):.3f} ms, threads={sorted(set(row["thread"] for row in rows))}')
    memory=groups.get('memory.sample',[])
    if memory:
        print('Memory:',json.dumps([{key:row.get(key) for key in ('timestamp','pid','rss_bytes','private_bytes','peak_rss_bytes','live_widgets','dropped_records')} for row in memory[-8:]]))


if __name__=='__main__':main()
# AUDIT-END
