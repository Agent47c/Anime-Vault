# AUDIT-START
"""Temporary passive audit hooks. Enabled only by APP_PROFILE=1.

No payloads, SQL parameter values, tokens, magnet links or search text are logged.
All writes happen on a dedicated logging thread, outside the GUI event loop.
"""
import atexit
import functools
import importlib.abc
import importlib.machinery
import inspect
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import sys
import threading
import time
import traceback
from datetime import datetime, timezone

ENABLED = os.environ.get('APP_PROFILE') == '1'
LOG_PATH = Path(__file__).resolve().parents[1] / 'audit_logs' / 'profile.jsonl'
_recorder = None
_original_connect = sqlite3.connect
_installed = False
_local = threading.local()


class Recorder:
    def __init__(self):
        self.events = queue.Queue(maxsize=50000)
        self.dropped = 0
        self.closed = False
        self.session = f'{os.getpid()}-{time.time_ns()}'
        self.started = time.perf_counter()
        self.thread = threading.Thread(target=self._write, name='AuditLogWriter', daemon=True)
        self.thread.start()

    def emit(self, action, duration_ms=0., item_count=None, **fields):
        if self.closed:
            return
        record = dict(timestamp=datetime.now(timezone.utc).isoformat(),
                      action=action, duration_ms=round(duration_ms, 3), item_count=item_count,
                      thread=threading.current_thread().name, thread_id=threading.get_ident(),
                      pid=os.getpid(), session=self.session, **fields)
        try:
            self.events.put_nowait(record)
        except queue.Full:
            self.dropped += 1

    def _write(self):
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Append only. Each process uses one write per complete JSON record.
            fd = os.open(str(LOG_PATH), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        except OSError:
            self.dropped += 1
            return
        try:
            while True:
                record = self.events.get()
                try:
                    if record is None:
                        return
                    data = (json.dumps(record, ensure_ascii=True, default=str) + '\n').encode('utf-8')
                    os.write(fd, data)
                except (OSError, ValueError):
                    self.dropped += 1
                finally:
                    self.events.task_done()
        finally:
            os.close(fd)

    def close(self):
        if self.closed:
            return
        self.emit('audit.session_end', dropped_records=self.dropped)
        self.closed = True
        try:
            self.events.put(None, timeout=.2)
            self.thread.join(timeout=2)
        except queue.Full:
            pass


def emit(action, duration_ms=0., item_count=None, **fields):
    if _recorder is not None:
        _recorder.emit(action, duration_ms, item_count, **fields)


def counts(value):
    """Only lengths and numeric identifiers; never stringify application objects."""
    result = {}
    if isinstance(value, (list, tuple, set)):
        result['item_count'] = len(value)
    elif isinstance(value, dict):
        for key in ('new', 'updated', 'skipped', 'files', 'file_count', 'folder_count'):
            if isinstance(value.get(key), (int, float)):
                result[key] = value[key]
        result['result_keys'] = len(value)
    else:
        for key in ('_cards', 'records', 'rows', 'items', 'slots', 'seasons', '_updates', '_health_records'):
            candidate = getattr(value, '__dict__', {}).get(key)
            if isinstance(candidate, (list, tuple, dict, set)):
                result[key.lstrip('_') + '_count'] = len(candidate)
    return result


def sql_label(sql):
    # Redact all SQL literals, including escaped single quotes and numeric IDs.
    value = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", '?', str(sql))
    value = re.sub(r'\b\d+(?:\.\d+)?\b', '?', value)
    return re.sub(r'\s+', ' ', value).strip()[:220]


class AuditCursor(sqlite3.Cursor):
    def execute(self, sql, parameters=()):
        started = time.perf_counter()
        self._audit_sql = sql_label(sql)
        try:
            return super().execute(sql, parameters)
        finally:
            emit('db.execute', (time.perf_counter()-started)*1000,
                 sql=self._audit_sql, row_count=self.rowcount,
                 row_count_note='SQLite -1 means not known before fetch')

    def executemany(self, sql, parameters):
        started = time.perf_counter(); self._audit_sql = sql_label(sql)
        try:
            return super().executemany(sql, parameters)
        finally:
            emit('db.executemany', (time.perf_counter()-started)*1000,
                 sql=self._audit_sql, row_count=self.rowcount)

    def executescript(self, sql):
        started = time.perf_counter(); self._audit_sql = sql_label(sql)
        try:
            return super().executescript(sql)
        finally:
            emit('db.executescript', (time.perf_counter()-started)*1000, sql=self._audit_sql)

    def fetchall(self):
        started=time.perf_counter(); rows=super().fetchall()
        emit('db.fetchall', (time.perf_counter()-started)*1000, len(rows), sql=getattr(self,'_audit_sql',''))
        return rows

    def fetchmany(self, size=None):
        started=time.perf_counter()
        rows=super().fetchmany() if size is None else super().fetchmany(size)
        emit('db.fetchmany', (time.perf_counter()-started)*1000, len(rows), sql=getattr(self,'_audit_sql',''))
        return rows

    def fetchone(self):
        started=time.perf_counter(); row=super().fetchone()
        emit('db.fetchone', (time.perf_counter()-started)*1000, int(row is not None), sql=getattr(self,'_audit_sql',''))
        return row

    def __iter__(self):
        return self

    def __next__(self):
        started=time.perf_counter()
        try:
            row=super().__next__()
        except StopIteration:
            emit('db.iteration', getattr(self,'_audit_iter_ms',0.), getattr(self,'_audit_iter_rows',0), sql=getattr(self,'_audit_sql',''))
            self._audit_iter_ms=0.;self._audit_iter_rows=0
            raise
        self._audit_iter_ms=getattr(self,'_audit_iter_ms',0.)+(time.perf_counter()-started)*1000
        self._audit_iter_rows=getattr(self,'_audit_iter_rows',0)+1
        return row


class AuditConnection(sqlite3.Connection):
    def cursor(self, factory=None):
        return super().cursor(factory or AuditCursor)

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql):
        return self.cursor().executescript(sql)

    def commit(self):
        started=time.perf_counter()
        try:
            return super().commit()
        finally:
            emit('db.commit', (time.perf_counter()-started)*1000)

    def backup(self, target, **kwargs):
        started=time.perf_counter()
        try:
            return super().backup(target, **kwargs)
        finally:
            emit('db.backup', (time.perf_counter()-started)*1000)


def connect(*args, **kwargs):
    started=time.perf_counter()
    # An explicit factory must keep its original semantics.
    if len(args)<6 and 'factory' not in kwargs:
        kwargs['factory']=AuditConnection
    try:
        return _original_connect(*args, **kwargs)
    finally:
        emit('db.connect', (time.perf_counter()-started)*1000)


# Only action/work boundaries, never delegates' paint/data calls or every line.
METHODS = set('''__init__ _setup_ui refresh refresh_display render loaded load reset
change_page _set_view_mode _on_sort_changed _on_filter_pill_clicked activate_filter
set_search_query _on_item_checked set_selection_mode _on_nav_clicked _refresh_dirty_page
_apply_refresh_snapshot _apply_refresh_step _refresh_metrics _on_data_updated
_open_detail_modal _on_update_choices_changed _apply_choices _render_cards
_set_text_size _on_theme_changed _apply_settings_preferences refresh_home_style
_reload_async _load_data _build_ui_steps _render_grid _render_compact _reflow_grid
resizeEvent wheelEvent enterEvent leaveEvent scrollContentsBy sync reflow set_records
image_ready request _finished run start check _ready snapshot call attach prepare
pause resume remove action bulk add search search_finished confirm_match apply
_start_scan _on_scan_finished _populate_table _apply_table_filter _execute_batch
generate_preview preview _preview_ready _execute stop import_media _apply
_on_import_clicked _on_search_clicked _on_apply_clicked _start_update_action
_update_action_finished _start_refresh _finish_refresh _connect_signals
_setup_tray _restore_geometry _initial_online_check _recover_file_operations
apply_scope update requestInterruption cancel _on_parse_finished _render
_on_results _on_match_results _apply_import _on_import_finished'''.split())
FUNCTIONS = set('''main apply_theme build_qss apply_preferences navigate prepare_details
cached_refresh_image load_cached_image refresh_pixmap valid_image _graphql_request
download_cover download_banner _download_image _download_artwork scan_watched_directories
collect_video_groups scan_roots collect_inventory scan_root build_inventory snapshot
poll jobs settings add_download add_torrent status action prepare_move move_file
recover_operations preview execute_plan scan_duplicates find_duplicates discover timeline
import_watching cached cached_icons read_message accept_message connected_loop
build_facts build_groups match_folder process_folder sync_folder index_local_folder
launch_video_file search_releases search sources import_txt_file init_db start_server
stop_server inventory checkpoint digest load_review delete_duplicate _cached_artwork
_add_builtin _index_completed control_builtin submit get_all_franchises
get_seasons_for_franchise get_library_stats get_series_seasons'''.split())
FUNCTIONS.update(('search_anime','get_anime_by_id','_rate_limit','_save_jobs','read_message','finish','claim','wait'))


def signature_proxy(function, measured):
    """Preserve the code-level arity PyQt uses when connecting Python slots.

    __wrapped__/__signature__ metadata alone does not preserve clicked(bool)
    argument trimming in PyQt5. Generate only parameter syntax, never reprs of
    defaults or annotations; their original objects are restored afterward.
    """
    signature=inspect.signature(function,follow_wrapped=False)
    parameters=list(signature.parameters.values());declarations=[];forward=[]
    has_varargs=False
    for index,parameter in enumerate(parameters):
        name=parameter.name;kind=parameter.kind
        if kind==inspect.Parameter.VAR_POSITIONAL:
            declarations.append('*'+name);forward.append('*'+name);has_varargs=True
        elif kind==inspect.Parameter.VAR_KEYWORD:
            declarations.append('**'+name);forward.append('**'+name)
        else:
            if kind==inspect.Parameter.KEYWORD_ONLY and not has_varargs:
                declarations.append('*');has_varargs=True
            declarations.append(name+('=None' if parameter.default is not inspect.Parameter.empty else ''))
            forward.append(name+'='+name if kind==inspect.Parameter.KEYWORD_ONLY else name)
            if kind==inspect.Parameter.POSITIONAL_ONLY and (index+1==len(parameters) or parameters[index+1].kind!=kind):
                declarations.append('/')
    target='__audit_measured_call'
    while target in signature.parameters:target+='_'  # Avoid shadowing by a parameter.
    namespace={target:measured,'__builtins__':{}}
    code=f"def _audit_forward({','.join(declarations)}):\n    return {target}({','.join(forward)})"
    exec(compile(code,'<audit-signature-proxy>','exec'),namespace)
    proxy=namespace['_audit_forward']
    proxy.__defaults__=function.__defaults__
    proxy.__kwdefaults__=function.__kwdefaults__
    functools.update_wrapper(proxy,function)
    proxy._audit_wrapped=True
    return proxy


def wrap(function, label):
    if getattr(function,'_audit_wrapped',False) or inspect.iscoroutinefunction(function) or inspect.isgeneratorfunction(function):
        return function
    @functools.wraps(function)
    def measured(*args, **kwargs):
        started=time.perf_counter();error=None;fields={}
        decodes=getattr(_local,'image_decodes',0)
        if label.endswith('load_cached_image'):_local.image_decodes=decodes+1
        if label.endswith('.run') and args:
            queued=getattr(args[0],'_audit_queued_at',None)
            if queued is not None:
                fields['queue_wait_ms']=round((started-queued)*1000,3)
        if label.endswith('cached_refresh_image') and args:
            module=sys.modules.get('app.ui.refresh')
            fields['cache_entries_before']=len(getattr(module,'_decoded_images',{}))
        if label.endswith('read_message') and args:
            # Framed input payload is counted after parsing; no contents retained.
            fields['transport']='native_messaging_stdio'
        if label.rsplit('.',1)[-1] in ('inventory','collect_video_groups','scan_root','scan_roots','index_local_folder') and args and isinstance(args[0],(str,Path)):
            fields['folder']=str(args[0])
        if label.endswith('EngineClient.call'):
            fields['command']=str(args[1] if len(args)>1 else kwargs.get('command','unknown'))[:40]
        result=None
        try:
            result=function(*args, **kwargs)
            if label.endswith('.__init__') and args and callable(getattr(args[0],'run',None)):
                namespace=getattr(args[0],'__dict__',None)
                if namespace is not None:namespace['_audit_queued_at']=time.perf_counter()
            if label.endswith('cached_refresh_image'):
                fields['cache_result']='miss' if getattr(_local,'image_decodes',0)!=decodes else ('missing_file' if result.isNull() else 'hit')
            info=kwargs.get('cache_info') or kwargs.get('info')
            if isinstance(info,dict):fields['cache_source']=info.get('source','unknown')
            if label.endswith('read_message') and isinstance(result,dict):
                action=result.get('action')
                fields['message_type']=action if action in ('capture','connect','heartbeat','search_result') else 'unknown'
                fields['message_bytes_estimated']=len(json.dumps(result,ensure_ascii=False).encode('utf-8'))
            if label.endswith('scan_state.inventory') and isinstance(result,tuple) and len(result)==2:
                fields['file_count']=len(result[1])
            if label.endswith('.timeline') and args and isinstance(args[0],int):fields['provider_id']=args[0]
            if label=='network.http':fields['status_code']=getattr(result,'status_code',None)
            return result
        except BaseException as exception:
            error=type(exception).__name__
            raise
        finally:
            duration=(time.perf_counter()-started)*1000
            fields.update(counts(args[0]) if args else {})
            fields.update(counts(result))
            emit(label,duration,error_type=error,**fields)
            if label.endswith('._on_nav_clicked'):
                from PyQt5.QtCore import QTimer
                index=args[1] if len(args)>1 else kwargs.get('index')
                emit('ui.tab_requested',duration,tab_index=index)
                QTimer.singleShot(0,lambda:emit('ui.tab_event_loop_return',(time.perf_counter()-started)*1000,tab_index=index,
                                               measurement='queued callback after handler; not GPU presentation'))
    return signature_proxy(function,measured)


def instrument_module(module):
    name=module.__name__
    for key,value in list(vars(module).items()):
        if inspect.isfunction(value) and value.__module__==name and key in FUNCTIONS:
            setattr(module,key,wrap(value,name+'.'+key))
        elif inspect.isclass(value) and value.__module__==name:
            for method,function in list(vars(value).items()):
                if method in METHODS and inspect.isfunction(function):
                    setattr(value,method,wrap(function,name+'.'+value.__name__+'.'+method))
    requests_module=sys.modules.get('requests.sessions')
    if requests_module is not None:
        session=requests_module.Session
        session.request=wrap(session.request,'network.http')


class AuditLoader:
    def __init__(self, loader):self.loader=loader
    def create_module(self,spec):return self.loader.create_module(spec)
    def exec_module(self,module):
        started=time.perf_counter()
        try:
            self.loader.exec_module(module)
            instrument_module(module)
        finally:
            emit('startup.import', (time.perf_counter()-started)*1000, module=module.__name__)


class AuditFinder(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith('app.') and fullname!='app.audit_profile':
            spec=importlib.machinery.PathFinder.find_spec(fullname,path)
            if spec is not None and hasattr(spec.loader,'exec_module'):
                spec.loader=AuditLoader(spec.loader)
            return spec
        return None


def memory_sample():
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(key,ctypes.c_size_t) for key in
                       ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                        'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]
        value=Counters();value.cb=ctypes.sizeof(value)
        process=ctypes.windll.kernel32.GetCurrentProcess
        process.restype=wintypes.HANDLE
        get=ctypes.windll.psapi.GetProcessMemoryInfo
        get.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if get(process(),ctypes.byref(value),value.cb):
            return dict(rss_bytes=value.WorkingSetSize,peak_rss_bytes=value.PeakWorkingSetSize,private_bytes=value.PrivateUsage)
    return dict(rss_bytes=None,peak_rss_bytes=None,private_bytes=None)


def attach(app, creation_ms=0.):
    """Attach timers to the existing Qt application; never replace QApplication."""
    if not ENABLED or hasattr(app,'_audit_probe'):return
    from PyQt5 import QtCore, QtWidgets
    import weakref
    application_ref=weakref.ref(app)
    class QtProbe(QtCore.QObject):
        def __init__(self):
            application=application_ref()
            super().__init__(application)
            self._audit_live=True
            emit('startup.QApplication',creation_ms)
            self._audit_main_thread=threading.get_ident()
            self._audit_last_heartbeat=time.perf_counter()
            self._audit_stopped=threading.Event()
            self._audit_heartbeat=QtCore.QTimer(self)
            self._audit_heartbeat.setTimerType(QtCore.Qt.PreciseTimer)
            self._audit_heartbeat.setInterval(50)
            self._audit_heartbeat.timeout.connect(self._audit_beat);self._audit_heartbeat.start()
            self._audit_memory=QtCore.QTimer(self);self._audit_memory.setInterval(15000)
            self._audit_memory.timeout.connect(self._audit_sample);self._audit_memory.start()
            self._audit_watch=threading.Thread(target=self._audit_watchdog,name='AuditWatchdog',daemon=True)
            self._audit_watch.start()
            application.aboutToQuit.connect(self._audit_stop)
            application.installEventFilter(self)
            QtCore.QTimer.singleShot(0,self._audit_first_turn)

        def _audit_first_turn(self):
            emit('startup.first_event_loop_turn',(time.perf_counter()-_recorder.started)*1000)
            self._audit_sample()

        def _audit_stop(self):
            self._audit_live=False
            application=application_ref()
            if application is not None:application.removeEventFilter(self)
            self._audit_heartbeat.stop();self._audit_memory.stop()
            self._audit_stopped.set()
            if self._audit_watch.ident is not None:self._audit_watch.join(timeout=.2)
            emit('audit.qt_stopped')

        def _audit_beat(self):
            now=time.perf_counter();late=(now-self._audit_last_heartbeat-.05)*1000
            if late>100:emit('gui.heartbeat_late',late,measurement='50ms timer excess delay; includes OS scheduling')
            self._audit_last_heartbeat=now

        def _audit_watchdog(self):
            previous=0.
            while not self._audit_stopped.wait(.025):
                now=time.perf_counter();late=(now-self._audit_last_heartbeat-.05)*1000
                if late>100 and now-previous>.25:
                    previous=now
                    frame=sys._current_frames().get(self._audit_main_thread)
                    # No locals or source lines: source lines can contain secrets.
                    stack=[dict(file=entry.filename,line=entry.lineno,function=entry.name) for entry in traceback.extract_stack(frame,limit=24)] if frame else []
                    emit('gui.stall_sample',late,stack=stack,measurement='sampled GUI Python stack; native/GIL attribution may be incomplete')

        def _audit_sample(self):
            application=application_ref()
            if application is None:return
            # allWidgets() can materialize wrappers for native-owned transient
            # widgets in PyQt5 and perturb destruction. Observe existing Python
            # wrappers only, without creating/retaining wrappers or forcing GC.
            import gc
            from PyQt5 import sip
            started=time.perf_counter();widgets=0
            for obj in gc.get_objects():
                try:
                    if isinstance(obj,QtWidgets.QWidget) and not sip.isdeleted(obj):widgets+=1
                except ReferenceError:pass
            emit('memory.sample',(time.perf_counter()-started)*1000,widgets,live_widgets=widgets,
                 widget_count_method='GC-tracked live QWidget wrappers; native-only widgets excluded',
                 live_threads=threading.active_count(),dropped_records=_recorder.dropped,**memory_sample())

        def eventFilter(self,receiver,event):
            if getattr(self,'_audit_live',False) and event.type() in (QtCore.QEvent.Wheel,QtCore.QEvent.MouseButtonRelease):
                started=time.perf_counter();kind=int(event.type());receiver_type=type(receiver).__name__
                emit('gui.input',event_type=kind,receiver_type=receiver_type)
                QtCore.QTimer.singleShot(0,lambda:emit('gui.input_event_loop_return',(time.perf_counter()-started)*1000,
                                                     event_type=kind,receiver_type=receiver_type))
            return False
    app._audit_probe=QtProbe()


def detach(app):
    probe=getattr(app,'_audit_probe',None)
    if probe is not None:
        from PyQt5 import sip
        if not sip.isdeleted(probe):
            probe._audit_stop()
            sip.delete(probe)
        del app._audit_probe


def bootstrap():
    global _installed,_recorder
    if not ENABLED or _installed:return
    _installed=True;_recorder=Recorder();atexit.register(_recorder.close)
    emit('audit.session_start',log_format=1,python=sys.version.split()[0],
         limitations='profiling adds overhead; SQL values and browser payloads omitted')
    sqlite3.connect=connect
    sys.meta_path.insert(0,AuditFinder())
    for name,module in list(sys.modules.items()):
        if name.startswith('app.') and module and name!='app.audit_profile':instrument_module(module)
    # Qt timers attach explicitly after QApplication is created. Native hosts
    # never import QtWidgets and retain their framed stdout channel.


# AUDIT-END
