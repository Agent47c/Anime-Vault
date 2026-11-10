"""Write a line-by-line presence report; optional backed-up missing-title import."""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.text_list_audit import audit,add_missing


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',action='append',required=True)
    parser.add_argument('--add-missing',action='store_true')
    parser.add_argument('--online',action='store_true')
    parser.add_argument('--report',default='data/text-list-presence.json')
    args=parser.parse_args();rows=audit(args.source);result=None
    if args.add_missing:
        result=add_missing(rows,online=args.online);rows=audit(args.source)
    report=dict(summary={source:dict(Counter(row['status'] for row in rows if row['file']==source)) for source in args.source},
                changes=result,rows=rows)
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=True))
    if result:print(json.dumps(result))
    print('Rows not represented:',sum(not row['ids'] for row in rows))
    print('Report:',path.resolve())

if __name__=='__main__':main()
