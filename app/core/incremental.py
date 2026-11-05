"""Only changed folder inventories enter parsing, indexing and API matching."""
from contextlib import closing
from pathlib import Path
import os
from app import db
from app.core import scan_state as state


def scan(progress_callback=None,scan_progress=None,new_only=False,allow_network=True):
    from app.core import scanner as sc
    cancelled = lambda: bool(scan_progress and (scan_progress.is_cancelled() if hasattr(scan_progress,'is_cancelled') else scan_progress.cancelled))
    processed,new,updated,unchanged,changed_files = 0,0,0,0,0
    errors,indexed_ids,states = [],set(),{}
    for watched in db.get_watched_directories():
        if cancelled():
            break
        root = Path(watched['folder_path']).resolve()
        try:
            # Enumerate explicitly: is_dir() alone can hide access failures.
            root.stat()
            children = list(root.iterdir())
        except FileNotFoundError as error:
            state.root_status(watched,'OFFLINE',str(error))
            states[str(root)] = 'OFFLINE'
            errors.append(f'{root}: root unavailable; saved inventory/history retained')
            continue
        except InterruptedError:
            raise
        except OSError as error:
            state.root_status(watched,'INACCESSIBLE',str(error))
            states[str(root)] = 'INACCESSIBLE'
            errors.append(f'{root}: {error}; saved inventory/history retained')
            continue
        inaccessible = False
        seen_scopes = set()
        for folder in sorted(children,key=lambda p:p.name.casefold()):
            if cancelled():
                break
            if folder.is_symlink() or not folder.is_dir():
                continue
            scope = state.key(folder)
            seen_scopes.add(scope)
            existing = db.find_franchise_by_folder_path(str(folder))
            if new_only and existing:
                unchanged += 1
                continue
            try:
                fingerprint,files = state.inventory(folder,cancelled)
                with closing(db.get_connection()) as conn:
                    previous = conn.execute('SELECT fingerprint FROM scan_scopes WHERE root_id=? AND scope=?',(watched['id'],scope)).fetchone()
                if previous and previous[0] == fingerprint:
                    state.restore_scope(watched['id'],scope)
                    unchanged += 1
                    continue
                changed,removed = state.changes(watched['id'],scope,files)
                changed_files += len(changed)+len(removed)
                name = sc.clean_title(folder.name)
                if progress_callback:
                    progress_callback(f'Indexing changes: {name}',processed+1,len(children))
                existing = existing or db.find_franchise_by_title(name) or db.find_franchise_by_title(folder.name)
                if existing:
                    sc._update_on_disk_info(existing['id'],str(folder),changed_paths=changed,inventory=files)
                    fid = existing['id']
                    updated += 1
                else:
                    fid = sc._create_from_folder({'path':str(folder),'name':folder.name},name,inventory=files)
                    new += bool(fid)
                if fid:
                    indexed_ids.add(fid)
                state.checkpoint(watched['id'],scope,fingerprint,files,fid)
                processed += 1
            except InterruptedError:
                raise
            except OSError as error:
                inaccessible = True
                errors.append(f'{folder}: {error}; incomplete inventory not saved')
        if cancelled():
            break
        # Direct-root loose videos have their own cheap metadata checkpoint.
        try:
            scope = state.key(root)+'|loose'
            seen_scopes.add(scope)
            fingerprint,files = state.inventory(root,cancelled,recursive=False)
            with closing(db.get_connection()) as conn:
                old = conn.execute('SELECT fingerprint FROM scan_scopes WHERE root_id=? AND scope=?',(watched['id'],scope)).fetchone()
            if not old or old[0] != fingerprint:
                changed,removed = state.changes(watched['id'],scope,files)
                from app.core.loose import inspect_loose_episodes
                groups,unknown = inspect_loose_episodes(root)
                for item in groups:
                    if cancelled():
                        raise InterruptedError('Scan cancelled')
                    if new_only:
                        with closing(db.get_connection()) as conn:
                            if conn.execute('SELECT 1 FROM seasons WHERE scan_root=? AND local_scan_key=?',(str(root),'loose-root:'+item['loose_key'])).fetchone():
                                continue
                    fid = sc.index_loose_group(item)
                    indexed_ids.add(fid)
                    updated += 1
                    processed += 1
                changed_files += len(changed)+len(removed)
                if not new_only:
                    state.checkpoint(watched['id'],scope,fingerprint,files,None)
            if not inaccessible:
                # A vanished child below a readable root is missing, not offline.
                with closing(db.get_connection()) as conn:
                    gone = conn.execute('SELECT scope,franchise_id,fingerprint FROM scan_scopes WHERE root_id=?',(watched['id'],)).fetchall()
                for row in gone:
                    if row['scope'] not in seen_scopes and row['fingerprint'] != 'missing':
                        state.checkpoint(watched['id'],row['scope'],'missing',{},row['franchise_id'])
            state.root_status(watched,'INACCESSIBLE' if inaccessible else 'ONLINE')
            states[str(root)] = 'INACCESSIBLE' if inaccessible else 'ONLINE'
            db.update_watched_directory_scan_time(watched['id'])
        except InterruptedError:
            raise
        except OSError as error:
            state.root_status(watched,'INACCESSIBLE',str(error))
            states[str(root)] = 'INACCESSIBLE'
            errors.append(f'{root}: {error}; saved inventory retained')
    if indexed_ids and allow_network and not cancelled() and not sc.is_offline():
        from app.core.matching import auto_match_indexed_folders
        from app.core.anilist_client import cancellable
        with cancellable(cancelled):
            errors.extend(auto_match_indexed_folders(cancelled,progress_callback,indexed_ids))
    return {'scanned':processed,'new':new,'updated':updated,'unchanged':unchanged,'changed_files':changed_files,'root_states':states,'errors':errors}
