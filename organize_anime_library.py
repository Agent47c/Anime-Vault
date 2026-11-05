"""Preview consolidation by default. Media moves require --apply and typing MOVE."""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from app.core.consolidation import make_plan, save_plan, apply_plan, sync_moved_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roots', nargs='+', default=[r'E:\New Anime Seasons', r'E:\Seen Anime'])
    parser.add_argument('--destination', default=r'E:\Anime Library')
    parser.add_argument('--overrides', type=Path, help='JSON mapping source anime folders to series/release names')
    parser.add_argument('--apply', type=Path, help='Reviewed plan.json to execute')
    args = parser.parse_args()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = Path(__file__).resolve().parent / 'data' / 'exports' / ('consolidation-' + stamp)
    if args.apply is None:
        overrides = json.loads(args.overrides.read_text(encoding='utf-8-sig')) if args.overrides else None
        plan = make_plan(args.roots, args.destination, overrides)
        save_plan(plan, output)
        print(f"Preview only: {len(plan['moves'])} planned files; {sum(bool(m['review_reason']) for m in plan['moves'])} need release review; {len(plan['unassigned'])} unassigned.")
        print(f"Errors: {len(plan['errors'])}. Reports: {output}")
        return
    plan = json.loads(args.apply.read_text(encoding='utf-8'))
    print(f"Destination: {plan['destination']}\nEligible moves: {sum(not m.get('review_reason') for m in plan['moves'])}")
    if input('Type MOVE to execute this reviewed plan (anything else cancels): ').strip() != 'MOVE':
        print('Cancelled. No files moved.')
        return
    from app import db
    db.init_db()
    output.mkdir(parents=True, exist_ok=False)
    source = db.get_connection()
    backup = sqlite3.connect(str(output / 'before-moves.db'))
    source.backup(backup)
    backup.close()
    source.close()
    result = apply_plan(plan, output / 'move-journal.jsonl')
    try:
        sync_moved_inventory(result['moved'], plan['destination'])
    except Exception as error:
        result['errors'].append({'source': 'library indexing', 'error': str(error)})
    (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f"Moved: {len(result['moved'])}; errors: {len(result['errors'])}; skipped for review: {result['skipped_review']}.\nJournal: {output}")


if __name__ == '__main__':
    main()
