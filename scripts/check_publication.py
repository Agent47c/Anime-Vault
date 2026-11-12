"""Check public-snapshot hygiene, file sizes and primary documentation links.

This checks tracked plus non-ignored files, or the index with --staged.
It is a focused guard, not a complete secret-scanner or security audit.
"""
import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
    'private-key':r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----',
    'github-token':r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'aws-key':r'AKIA[0-9A-Z]{16}',
    'google-api-key':r'AIza[0-9A-Za-z_-]{35}',
}
PRIVATE_SUFFIXES={'.db','.sqlite','.sqlite3','.pem','.key','.fastresume','.torrent','.mkv','.mp4','.avi','.webm','.dmp'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--staged',action='store_true');args=parser.parse_args()
    command=['git','ls-files','--cached','-z']
    if not args.staged:command.extend(['--others','--exclude-standard'])
    names=set(subprocess.check_output(command,cwd=ROOT).decode('utf-8').split('\0'))-{''}
    errors=[];total=0;text_count=0
    for name in sorted(names):
        path=ROOT/name
        raw=subprocess.check_output(['git','show',':'+name],cwd=ROOT) if args.staged else path.read_bytes()
        total+=len(raw)
        if path.suffix.lower() in PRIVATE_SUFFIXES or path.name=='.env' or (name.startswith('data/') or (name.startswith('audit_logs/') and name!='audit_logs/CHANGES.md')):
            errors.append((name,'private/runtime file'))
        if len(raw)>95*1024**2:errors.append((name,'exceeds 95 MiB publication limit'))
        try:content=raw.decode('utf-8')
        except UnicodeDecodeError:continue
        text_count+=1
        for label,pattern in PATTERNS.items():
            if re.search(pattern,content):errors.append((name,label))
        if name=='README.md' or name.startswith('docs/') and path.suffix=='.md':
            for match in re.finditer(r'\]\(([^)]+)\)',content):
                target=match[1].strip('<>')
                parsed=urlsplit(target)
                if parsed.scheme or not parsed.path:continue
                resolved=(path.parent/unquote(parsed.path)).resolve()
                if not resolved.exists():errors.append((name,'missing linked file: '+target))
                elif resolved.is_file() and resolved.relative_to(ROOT).as_posix() not in names:errors.append((name,'linked file not in public snapshot: '+target))
    print(f'Publication check: {len(names)} files, {text_count} text files, {total/1024**2:.1f} MiB')
    for path,label in errors:print(f'ERROR {path}: {label}')
    if errors:return 1
    print('No guarded secret patterns, private/runtime files, oversized files or missing primary documentation links found.')
    return 0


if __name__=='__main__':raise SystemExit(main())
