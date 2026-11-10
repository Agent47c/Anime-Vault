"""Revisitable five-step download setup using the existing drawer and IO worker."""
from PyQt5.QtCore import Qt,QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QStackedWidget,QLineEdit,QComboBox,QFileDialog,QProgressBar
from pathlib import Path
import json
from app import db
from app.core import downloads
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,field,button
from app.ui.magnet_capture import review_text as text
from app.ui.io_task import start


class DownloadSetup(DrawerDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.step=0;self.checked=False
        config=downloads.settings()
        body,self.next_button=chrome(self,'Set up downloads','Five small steps. You can return here at any time.','取込','Next',self.advance)
        self.setProperty('setupFlow',True)
        self.progress=text('Step 1 of 5 · Chrome extension','workflow_row_title');body.addWidget(self.progress)
        self.steps=json.loads(db.get_state('download_setup.progress','["Not checked","Not checked","Not checked","Not checked","Not checked"]'))
        self.overview=text('');body.addWidget(self.overview);self.render_steps()
        self.stack=QStackedWidget();self.stack.setObjectName('setup_steps');body.addWidget(self.stack,1)
        self.titles=['Chrome extension','Download engine','Download folder','Sources and preferences','Test and finish']
        columns=[]
        for _ in range(5):
            page=QWidget();page.setObjectName('workflow_field');column=QVBoxLayout(page);column.setContentsMargins(0,0,0,0);column.setSpacing(16)
            self.stack.addWidget(page);columns.append(column)
        box=columns[0]
        box.addWidget(text('Load the Anime Vault folder in chrome://extensions with Developer mode enabled. Copy its extension ID below. After connecting, enable the same website selected in step 4.'))
        self.extension=QLineEdit(db.get_state('chrome.capture_extension',''));field(box,'Chrome extension ID',self.extension)
        box.addWidget(button('Open extension folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[2]/'browser-extension')))))
        box.addWidget(button('Continue with manual magnets for now',self.skip_extension))
        box.addStretch()
        box=columns[1];self.engine=QComboBox();self.engine.addItem('Anime Vault built-in downloader','builtin');self.engine.setEnabled(False)
        field(box,'Download engine',self.engine)
        box.addWidget(text('Downloads run inside Anime Vault. No other torrent app, Web UI, username or password is required.'));box.addStretch()
        box=columns[2];self.destination=QLineEdit(config['destination']);field(box,'Save new downloads in',self.destination)
        box.addWidget(button('Choose folder',self.choose_folder));box.addWidget(text('Downloads use isolated subfolders. Existing library files will not be moved.'));box.addStretch()
        box=columns[3]
        self.source=QLineEdit(config['source']);field(box,'Source search URL — include {query}',self.source)
        self.group=QLineEdit(config['group']);field(box,'Default release group (optional)',self.group)
        self.quality=QLineEdit(config['quality']);field(box,'Default quality (optional)',self.quality)
        box.addWidget(text('Example: https://nyaa.si/?q={query}&f=0&c=0_0. Other sites need readable magnet links. Enable this exact website in the Chrome popup.'));box.addStretch()
        box=columns[4];self.results=text('Test the download engine, folder access and live Chrome/source connection.');box.addWidget(self.results)
        box.addWidget(button('Save and finish later',self.accept));box.addStretch()
        self.status=text('Your existing library and transfers remain available.');body.addWidget(self.status)
        self.loading=QProgressBar();self.loading.setRange(0,0);self.loading.setFixedHeight(4);self.loading.hide();body.addWidget(self.loading)
        body.addWidget(button('Back',self.back))

    def choose_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Choose download folder',self.destination.text())
        if path:self.destination.setText(path)

    def skip_extension(self):
        self.record_step(0,'Skipped for manual magnets')
        self.status.setText('Chrome setup skipped. Pasted magnets and .torrent files remain available.');self.show_step(1)

    def show_step(self,index):
        self.checked=False
        self.step=index;self.stack.setCurrentIndex(index);self.progress.setText(f'Step {index+1} of 5 · {self.titles[index]}')
        self.next_button.setText('Test connections' if index==4 else 'Next')

    def back(self): self.show_step(max(0,self.step-1))

    def render_steps(self):
        self.overview.setText(' · '.join(name+': '+state for name,state in zip(['Chrome','Engine','Folder','Sources','Test'],self.steps)))

    def record_step(self,index,state):
        self.steps[index]=state;db.set_state('download_setup.progress',json.dumps(self.steps));self.render_steps()

    def advance(self):
        if self.step==0:
            from app.core.chrome_bridge import register
            identifier=self.extension.text().strip()
            def connected(message):
                host=self.window()
                if hasattr(host,'_magnet_inbox'):host._magnet_inbox.enable()
                self.record_step(0,'Registered — enable in Chrome');self.status.setText(message);self.show_step(1)
            start(self,lambda:register(identifier),connected)
        elif self.step<4:
            config={'engine':'builtin',
                    'destination':self.destination.text().strip(),'source':self.source.text().strip(),'group':self.group.text().strip(),
                    'quality':self.quality.text().strip(),'enabled':True}
            secret=None;following=self.step+1
            step=self.step
            start(self,lambda:downloads.save_settings(config,secret),lambda _:(self.record_step(step,'Configured — test in final step'),self.status.setText('Step saved.'),self.show_step(following)))
        elif self.checked: self.accept()
        else:
            from app.core.download_setup import checks
            self.loading.show();self.status.setText('Testing engine, folder and Chrome/source connection…')
            def done(result):
                self.results.setText('\n\n'.join(key.capitalize()+': '+value for key,value in result.items()))
                self.checked=not any(value.startswith(('Failed:','Needs attention:')) for value in result.values())
                self.steps=['Complete' if not result[key].startswith(('Failed:','Needs attention:')) else 'Needs attention' for key in ('extension','engine','folder','source')]+['Complete' if self.checked else 'Needs attention']
                db.set_state('download_setup.progress',json.dumps(self.steps));self.render_steps()
                self.next_button.setText('Finish setup' if self.checked else 'Retry connections')
                self.status.setText('Setup complete.' if self.checked else 'Fix the steps above, or save and finish later.')
            start(self,lambda:checks(test_source=True,cancelled=lambda:bool(getattr(self,'_apply_worker',None) and self._apply_worker.isInterruptionRequested())),done)
            self._apply_worker.finished.connect(self.loading.hide)


def open_setup(parent):
    from app.ui.navigation import navigate
    def finished(_):
        config=getattr(parent,'download_config',None)
        if config:config.reload_settings()
    navigate(DownloadSetup(parent),finished)
