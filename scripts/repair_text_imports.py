"""Preview by default; --apply backs up and repairs only proven import artifacts."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.import_repair import plan, apply_repair

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',action='append',default=[])
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--report',default='data/text-import-repair-report.json')
    args=parser.parse_args();preview=plan(args.source)
    report={key:value for key,value in preview.items() if key not in ('snapshot','overrides')}
    if args.apply:report['result']=apply_repair(preview)
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Title repairs:',len(preview['updates']),'Duplicate groups:',len(preview['groups']),'Ambiguous records left unchanged:',len(preview['ambiguous']))
    if args.apply:print(json.dumps(report['result']))
    print('Report:',path.resolve())

if __name__=='__main__':main()
