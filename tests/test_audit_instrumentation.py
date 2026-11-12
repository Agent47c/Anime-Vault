# AUDIT-START
"""Audit instrumentation must preserve SQL behavior and remain opt-in."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import inspect
from app import audit_profile as audit


class AuditInstrumentationTests(unittest.TestCase):
    def test_sql_cursor_rows_transactions_and_backup_preserved(self):
        source=sqlite3.connect(':memory:',factory=audit.AuditConnection)
        target=sqlite3.connect(':memory:')
        try:
            source.row_factory=sqlite3.Row
            source.execute('CREATE TABLE sample(id INTEGER PRIMARY KEY,value TEXT)')
            source.executemany('INSERT INTO sample(value) VALUES (?)',[('first',),('second',)])
            source.commit()
            self.assertEqual(source.execute('SELECT * FROM sample').fetchone()['value'],'first')
            self.assertEqual(len(source.execute('SELECT * FROM sample').fetchall()),2)
            self.assertEqual(len(source.execute('SELECT * FROM sample').fetchmany(1)),1)
            self.assertEqual(len(list(source.execute('SELECT * FROM sample'))),2)
            with self.assertRaises(ValueError):
                with source:
                    source.execute('DELETE FROM sample');raise ValueError('rollback')
            self.assertEqual(source.execute('SELECT count(*) FROM sample').fetchone()[0],2)
            source.backup(target)
            self.assertEqual(target.execute('SELECT count(*) FROM sample').fetchone()[0],2)
            with self.assertRaises(sqlite3.IntegrityError):source.execute('INSERT INTO sample VALUES (1,?)',('collision',))
        finally:source.close();target.close()

    def test_sql_labels_omit_values_and_limit_length(self):
        value=audit.sql_label("SELECT 'SECRET', 'escaped''quote' FROM sample WHERE id=12345")
        self.assertNotIn('SECRET',value);self.assertNotIn('12345',value);self.assertNotIn('escaped',value)
        self.assertLessEqual(len(audit.sql_label('SELECT '+('x '*1000))),220)

    def test_wrapped_function_preserves_return_value_and_exception(self):
        def original(value):
            if value is None:raise ValueError('same exception')
            return value
        wrapped=audit.wrap(original,'audit.fixture')
        sentinel=object();self.assertIs(wrapped(sentinel),sentinel)
        with self.assertRaisesRegex(ValueError,'same exception'):wrapped(None)
        self.assertIs(audit.wrap(wrapped,'audit.fixture'),wrapped)

    def test_proxy_preserves_real_arity_and_parameter_binding(self):
        default=object()
        def original(first,/,second=default,*values,required,optional=default,**extras):
            return first,second,values,required,optional,extras
        wrapped=audit.wrap(original,'audit.fixture.signature')
        self.assertEqual(wrapped.__code__.co_argcount,original.__code__.co_argcount)
        self.assertEqual(wrapped.__code__.co_posonlyargcount,original.__code__.co_posonlyargcount)
        self.assertEqual(wrapped.__code__.co_kwonlyargcount,original.__code__.co_kwonlyargcount)
        self.assertEqual(inspect.signature(wrapped,follow_wrapped=False),inspect.signature(original))
        self.assertEqual(wrapped(1,required=2),original(1,required=2))
        self.assertEqual(wrapped(1,3,4,5,required=2,custom=6),original(1,3,4,5,required=2,custom=6))
        with self.assertRaises(TypeError):wrapped(first=1,required=2)
        with self.assertRaises(TypeError):wrapped(1)

    def test_wrapped_qt_slots_and_real_search_click_in_profiled_subprocess(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,str(root/'scripts'/'audit_smoke.py'),'--signals'],
                              cwd=root,check=True,timeout=30,capture_output=True,text=True)
        self.assertIn('Qt signal matrix and ReleaseSearchPage button search passed',result.stdout)

    def test_disabled_bootstrap_does_not_patch_database_or_qt(self):
        code="import sqlite3; before=sqlite3.connect; from app.audit_profile import bootstrap; bootstrap(); assert sqlite3.connect is before"
        env=dict(os.environ,APP_PROFILE='0')
        subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env,check=True,timeout=20,capture_output=True)

    def test_enabled_native_host_keeps_stdout_clean_and_avoids_qt(self):
        code="import sys; sys.argv.append('--native-magnet-host'); from app.audit_profile import bootstrap; bootstrap(); assert 'PyQt5.QtWidgets' not in sys.modules; print('FRAMED_CHANNEL_UNCHANGED')"
        env=dict(os.environ,APP_PROFILE='1')
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env,check=True,timeout=20,capture_output=True,text=True)
        self.assertEqual(result.stdout.strip(),'FRAMED_CHANNEL_UNCHANGED')

    def test_full_window_profile_smoke_exits_cleanly_with_temporary_data(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,'-X','faulthandler',str(root/'scripts'/'audit_smoke.py'),'--app'],
                              cwd=root,check=True,timeout=30,capture_output=True,text=True)
        self.assertIn('empty temporary DB, offline, no API server',result.stdout)
        self.assertNotIn('fatal exception',result.stderr)
# AUDIT-END
