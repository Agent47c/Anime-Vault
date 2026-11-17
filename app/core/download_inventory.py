"""Tracked-file readiness shared by scanning, organization and move previews.

This is a file ownership/state check, not a folder exclusion rule. Untracked
neighbouring files retain ordinary scanner behaviour.
"""
import json
from pathlib import Path


class InventoryDeferred(OSError):
    pass


def ready(job):
    state=(job.get('status') or '').lower()
    return bool(job.get('indexed') and job.get('verified_files') and
                not job.get('integrity_missing') and not job.get('library_move_intent') and
                state not in ('downloading','checking files','fetching torrent metadata') and
                not any(word in state for word in ('error','failed','needs review','missing','unconfirmed')))


def signature(jobs):
    """Ignore byte counters/rates; only ownership and readiness change scans."""
    return json.dumps([dict(id=j.get('id'),fid=j.get('fid'),root=j.get('root'),
        destination=j.get('destination'),ready=ready(j),indexed=j.get('indexed'),cancelled=j.get('desired')=='cancelled',
        moved=j.get('library_moved'),missing=j.get('integrity_missing'),
        files=j.get('verified_files'),intent=j.get('library_move_intent'),move_error=j.get('library_move_error'))
        for j in jobs],sort_keys=True)


class Snapshot:
    def __init__(self,jobs=None):
        if jobs is None:
            from app.core.downloads import jobs as read_jobs
            jobs=read_jobs()
        self.jobs=jobs;self.owners=[];self.files={};self.targets={};self.paths={};self.aliases={};self.building=True;self.manually_organized=set()
        for job in jobs:
            if job.get('root'):
                raw=Path(job['root']).absolute();resolved=self.path(raw);self.owners.append((resolved,job))
                self.aliases.update(zip((raw,*raw.parents),(resolved,*resolved.parents)))
            for file in job.get('verified_files') or []:self.files[self.path(file['path'])]=job
            self.manually_organized.update(self.path(p) for p in job.get('manually_organized_files',[]))
            for row in job.get('library_move_intent') or []:self.targets[self.path(row['target'])]=job
        self.owners.sort(key=lambda item:len(item[0].parts),reverse=True)
        self.aliases=sorted(self.aliases.items(),key=lambda pair:len(pair[0].parts),reverse=True);self.building=False
    def owner(self,path):
        if not(self.owners or self.files or self.targets):return None
        path=self.path(path)
        if path in self.targets:return self.targets[path]
        if path in self.files:return self.files[path]
        return next((job for root,job in self.owners if path==root or path.is_relative_to(root)),None)
    def can_index(self,path):
        job=self.owner(path)
        return job is None or (ready(job) and self.path(path) in self.files)
    def can_scan_library(self,path):
        job=self.owner(path)
        # Completion is indexed once through the job's explicit anime link.
        # The ordinary folder scanner must not invent an anime from a job name.
        return job is None or ((job.get('library_moved') or self.path(path) in self.manually_organized) and self.can_index(path))
    def assert_scan_scope(self,folder,recursive=True):
        self.assert_not_moving(folder,recursive);folder=self.path(folder)
        if any(not job.get('library_moved') and (folder==root or folder.is_relative_to(root)) for root,job in self.owners):
            raise InventoryDeferred('This tracked download keeps its saved anime association; ordinary folder indexing is deferred.')
    def path(self,path):
        key=str(path)
        if key not in self.paths:
            value=Path(path).absolute()
            if self.building:value=value.resolve()
            else:
                for raw,resolved in self.aliases:
                    if value==raw or value.is_relative_to(raw):value=resolved/value.relative_to(raw);break
            self.paths[key]=value
        return self.paths[key]
    def can_organize(self,path):
        return self.can_scan_library(path)
    def in_staging(self,path):
        if not self.owners:return False
        path=self.path(path)
        return any(path==root or path.is_relative_to(root) for root,job in self.owners)
    def assert_not_moving(self,folder,recursive=True):
        folder=self.path(folder)
        for job in self.jobs:
            for row in job.get('library_move_intent') or []:
                if any((self.path(row[key]).is_relative_to(folder) or folder.is_relative_to(self.path(row[key]))) if recursive else self.path(row[key]).parent==folder for key in ('source','target')):
                    raise InventoryDeferred('Files are moving to the library; keep the previous inventory until the move finishes.')


def organizer_rows(jobs=None):
    from app import db
    if jobs is None:
        from app.core.downloads import jobs as read_jobs
        jobs=read_jobs()
    if not jobs:return []
    hidden=set(json.loads(db.get_state('library.removed_ids','[]')))
    groups={member:series for series in db.get_series_library() for member in series['series_member_ids']}
    rows=[]
    for job in jobs:
        fid=job.get('fid')
        if not fid or fid in hidden or job.get('library_moved'):continue
        series=groups.get(fid) or db.get_franchise(fid)
        if not series:continue
        complete=ready(job);review_move=bool(job.get('library_move_intent') and job.get('library_move_error'))
        if not complete and job.get('desired')=='cancelled' and not job.get('library_move_intent'):continue
        label='Move needs review' if review_move else 'Download ready' if complete else 'Moving to library' if job.get('library_move_intent') else 'Download not ready'
        rows.append(dict(anime_name=series['display_title'],folder_path=job.get('destination') or job.get('root',''),
            franchise_id=fid,download_job_id=job['id'],download_ready=complete or review_move,
            video_count=len(job.get('verified_files') or []) if complete or review_move else 0,is_organized=False,
            status_badge=label,status_reason=job['library_move_error'] if review_move else 'Completed download — review move to its anime and season folder' if complete else
            'Wait for verified completion before organizing this tracked download.',moves=[]))
    return rows
