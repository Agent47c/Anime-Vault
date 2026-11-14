"""One-time, collision-checked archive of design references and historical notes.

Run without arguments to preview; --apply moves only explicit workspace paths.
Runtime source, entry points, databases, media and installed builds stay put.
"""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from urllib.parse import unquote,urlsplit,quote

ROOT=Path(__file__).resolve().parents[1]
DESIGNS=('5 ui screen','add entry screen and txt importer screen','Anime Detail Screen',
 'Anime Library List View','Anime Valt Installer Pkg','Anime Vault — Unified Dropdown & Popover Menus System',
 'anime-vault-ui','choose episode page','confirm series grouping screen','edit season number ui screen',
 'file download page','final ui','find download file page ui','Home Library Screen','merge and duplicate ui',
 'new anime release screen','organizer screen','Review duplicate files screen','Sertting UI','setting ui screen',
 'Unified Button Design System & Component Template','update and download screen')
KEEP={'README.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','PRIVACY.md'}
GUIDES={'All Feature and their Navigation.md','ORGANIZER_USAGE.md'}


def checked(path):
    target=path.resolve()
    if not target.is_relative_to(ROOT.resolve()):raise ValueError('Path escaped workspace: '+str(path))
    if path.is_symlink() or path.is_junction():raise ValueError('Linked paths require manual review: '+str(path))
    return path


def plan():
    moves={}
    for name in DESIGNS:
        if (ROOT/name).is_dir():moves[name]='design/references/'+name
    for path in ROOT.glob('*.md'):
        if path.name not in KEEP:
            folder='guides' if path.name in GUIDES else 'planning' if path.name in ('new feature to be added.md','anime_library_storage_manager_production_specification.md') else 'history'
            moves[path.name]='docs/'+folder+'/'+path.name
    for path in ROOT.glob('*-preview.png'):moves[path.name]='design/previews/'+path.name
    if (ROOT/'ui.html').is_file():moves['ui.html']='design/references/legacy-ui/ui.html'
    for name in ('Deleted Seen Anime 1.txt','Seen And Deleted Animes.txt'):
        if (ROOT/name).is_file():moves[name]='data/import-lists/'+name
    for name,dest in [('browser-extension.pem','data/private/browser-extension.pem'),('browser-extension.crx','dist/browser-extension/browser-extension.crx'),('Tac','tools/external-installers/Tac')]:
        if (ROOT/name).exists():moves[name]=dest
    return moves


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    moves=plan();files={};documents={}
    for old,new in moves.items():
        source=checked(ROOT/old);destination=checked(ROOT/new)
        if destination.exists():raise FileExistsError(str(destination))
        children=list(source.rglob('*')) if source.is_dir() else [source]
        for child in children:
            checked(child)
            if child.is_file():
                relative=child.relative_to(ROOT).as_posix();target=ROOT/new/child.relative_to(source) if source.is_dir() else ROOT/new
                files[relative]=target.relative_to(ROOT).as_posix()
    for area in (ROOT,ROOT/'docs',ROOT/'design'):
        candidates=area.glob('*.md') if area==ROOT else area.rglob('*.md')
        for path in candidates:
            if path.is_file():documents[path.relative_to(ROOT).as_posix()]=path.read_text(encoding='utf-8')
    # Read design docs before their parent directories move too.
    for old in files:
        if old.endswith('.md') and old not in documents:documents[old]=(ROOT/old).read_text(encoding='utf-8')
    print(json.dumps(moves,ensure_ascii=False,indent=2));print(f'{len(moves)} top-level moves; {len(files)} files.')
    if not args.apply:return
    digests={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
    for old,new in moves.items():
        source=checked(ROOT/old);destination=checked(ROOT/new);destination.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(destination))
    for old,new in files.items():
        if hashlib.sha256((ROOT/new).read_bytes()).hexdigest()!=digests[old]:raise RuntimeError('Move checksum mismatch: '+new)
    # Preserve Markdown links relative to each document's new location. Historical
    # prose and bare file names remain unchanged; only actual local links move.
    updated=[]
    for old,content in documents.items():
        new=files.get(old,old);path=ROOT/new
        def replace(match):
            value=match[1];raw=value.strip('<>');parsed=urlsplit(raw)
            if parsed.scheme or not parsed.path or raw.startswith('#'):return match[0]
            original=(ROOT/old).parent/unquote(parsed.path)
            try:relative=original.resolve().relative_to(ROOT).as_posix()
            except ValueError:return match[0]
            target=ROOT/files.get(relative,relative)
            if not target.exists():return match[0]
            import os
            link=quote(Path(os.path.relpath(target,path.parent)).as_posix(),safe='/.-_')
            if parsed.fragment:link+='#'+parsed.fragment
            return ']('+link+')'
        result=re.sub(r'\]\(([^)]+)\)',replace,content)
        if result!=content:path.write_text(result,encoding='utf-8');updated.append(new)
    record={'date':'2026-11-14','moves':moves,'files':[{'from':old,'to':new,'original_sha256':digests[old]} for old,new in files.items()],'updated_markdown_links':updated}
    report=ROOT/'docs/maintenance/workspace-organization-2026-11-14.json';report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Verified all {len(files)} file contents after moving; repaired links in {len(updated)} documents.')


if __name__=='__main__':main()
