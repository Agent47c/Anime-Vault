# AUDIT-START
"""Instrumentation verification only, with a temporary database and no network."""
import os
import sys
os.environ['APP_PROFILE']='0' if '--baseline' in sys.argv else '1';os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.audit_profile import bootstrap,emit,attach,detach
bootstrap()
import tempfile
import time
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication,QWidget
from app import db


def main():
    with tempfile.TemporaryDirectory(prefix='anime-vault-audit-') as directory:
        root=Path(directory)
        db.DATA_DIR=root;db.DB_PATH=root/'audit-test.db';db.COVERS_DIR=root/'covers';db.EXPORTS_DIR=root/'exports'
        started=time.perf_counter();app=QApplication([]);attach(app,(time.perf_counter()-started)*1000);db.init_db()
        if '--signals' in sys.argv:
            from app import config
            config.DATA_DIR=root;config.COVERS_DIR=db.COVERS_DIR;config.EXPORTS_DIR=db.EXPORTS_DIR;config.OFFLINE_MODE=True
            from app.audit_profile import wrap
            from PyQt5.QtWidgets import QPushButton,QAction,QComboBox,QCheckBox,QLineEdit
            from PyQt5.QtTest import QTest
            from unittest.mock import patch
            emit('audit.signal_smoke_begin',fixture=True)
            class Receiver:
                def __init__(self):self.calls=[]
                def zero(self):self.calls.append(('zero',))
                def one(self,value='default'):self.calls.append(('one',value))
                def variadic(self,*values):self.calls.append(('variadic',values))
            for name in ('zero','one','variadic'):setattr(Receiver,name,wrap(getattr(Receiver,name),'audit.fixture.'+name))
            receiver=Receiver();button=QPushButton();action=QAction();combo=QComboBox();check=QCheckBox();edit=QLineEdit()
            combo.addItems(['a','b'])
            for signal in (button.clicked,action.triggered,combo.currentIndexChanged,check.toggled,edit.textChanged,edit.returnPressed):
                signal.connect(receiver.zero);signal.connect(receiver.one);signal.connect(receiver.variadic)
            button.clicked.emit(True);action.triggered.emit(False);combo.setCurrentIndex(1);check.setChecked(True);edit.setText('fixture');edit.returnPressed.emit()
            assert len([row for row in receiver.calls if row[0]=='zero'])==6
            assert [row[1] for row in receiver.calls if row[0]=='one']==[True,False,1,True,'fixture','default']
            from app.ui.pages.release_search_page import ReleaseSearchPage
            from app.core import download_discovery as discovery
            fid=db.upsert_franchise(dict(display_title='Search fixture'))
            context=dict(fid=fid,title='Search fixture',aliases=['Search fixture'],continuous=False,season=1,local={},pending=[],expected=[],boundaries={},download_aliases=[])
            page=ReleaseSearchPage(None,fid);page.show()
            with patch.object(discovery,'search',return_value=dict(context=context,results=[])) as search:
                page.search_button.click()
                end=time.monotonic()+4
                while page._worker is not None and time.monotonic()<end:QTest.qWait(10)
                assert search.call_count==1
                assert page._worker is None and 'No releases found' in page.status.text()
            page.reject();page.deleteLater();QTest.qWait(10);detach(app)
            # Check every loaded instrumented callback, not only Search.
            import inspect
            checked=0
            for name,module in list(sys.modules.items()):
                if not name.startswith('app.') or module is None:continue
                for value in list(vars(module).values()):
                    members=list(vars(value).values()) if inspect.isclass(value) and value.__module__==name else [value]
                    for member in members:
                        if inspect.isfunction(member) and getattr(member,'_audit_wrapped',False):
                            original=member.__wrapped__
                            for attribute in ('co_argcount','co_posonlyargcount','co_kwonlyargcount'):
                                assert getattr(member.__code__,attribute)==getattr(original.__code__,attribute),(member.__qualname__,attribute)
                            checked+=1
            emit('audit.signal_smoke_end',fixture=True)
            print(f'Qt signal matrix and ReleaseSearchPage button search passed with profiling enabled; {checked} wrapped callback signatures verified.')
            return
        if '--app' in sys.argv:
            from app import config
            config.DATA_DIR=root;config.COVERS_DIR=db.COVERS_DIR;config.EXPORTS_DIR=db.EXPORTS_DIR
            config.OFFLINE_MODE=True
            db.set_state('scan_schedule','manual')
            from app.ui.main_window import MainWindow
            emit('audit.full_window_smoke_begin',fixture=True)
            window=MainWindow();window.show()
            def stop():
                if window._cleanup_and_exit():app.quit()
                else:QTimer.singleShot(100,stop)
            QTimer.singleShot(1000,stop)
            app.exec_();detach(app);window.hide()
            # Dispose the fixture tree while QApplication is still alive,
            # instead of leaving C++ widget destruction to interpreter teardown.
            from PyQt5.QtCore import QCoreApplication,QEvent
            window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            import gc
            gc.collect()
            emit('audit.full_window_smoke_end',fixture=True)
            print('Full window instrumentation verified with empty temporary DB, offline, no API server.')
            return
        # Verify SQL row/value behavior and literal redaction without user data.
        conn=db.get_connection()
        try:
            conn.execute('CREATE TABLE audit_fixture (value TEXT)')
            conn.executemany('INSERT INTO audit_fixture VALUES (?)',[('private-value',),('second',)])
            assert len(conn.execute('SELECT * FROM audit_fixture').fetchall())==2
            assert len(list(conn.execute('SELECT * FROM audit_fixture')))==2
            assert conn.execute("SELECT 'DO_NOT_LOG_THIS_LITERAL'").fetchone()[0]=='DO_NOT_LOG_THIS_LITERAL'
            conn.commit()
        finally:conn.close()
        window=QWidget();window.resize(600,400);window.show()
        emit('audit.smoke_begin',item_count=2,fixture=True)
        # Deliberate 180 ms blocking callback verifies the watchdog; it is not an app finding.
        QTimer.singleShot(100,lambda:time.sleep(.18))
        QTimer.singleShot(500,app._audit_probe._audit_sample)
        QTimer.singleShot(700,app.quit)
        app.exec_();detach(app);window.close()
        emit('audit.smoke_end',fixture=True)
    print('Audit smoke verification completed with a temporary database only.')


if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        traceback.print_exc(file=sys.__stdout__)
        raise
# AUDIT-END
