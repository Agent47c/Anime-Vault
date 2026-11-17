"""Month navigation over saved broadcasts; reuse existing preview/detail actions."""
import calendar
from datetime import date,timedelta
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QWidget,QGridLayout
from app.ui.components.airing_count import AiringDay
from app.ui.io_task import IOTask,track
from app.ui.home_style import colors


class FullCalendarPage(QDialog):
    full_page=True
    dispose_on_leave=True
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('Full Calendar');self.month=date.today().replace(day=1);self.worker=None;self.generation=0
        layout=QVBoxLayout(self);heading=QHBoxLayout();self.title=QLabel();heading.addWidget(self.title,1)
        for text,delta in [('Previous month',-1),('This month',0),('Next month',1)]:
            button=QPushButton(text);button.clicked.connect(lambda checked=False,d=delta:self.change(d));heading.addWidget(button)
            button.setCursor(Qt.PointingHandCursor)
        layout.addLayout(heading);self.status=QLabel('Saved library broadcasts · local time. Dates outside cached provider coverage may be empty.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.setObjectName('home_library');self.setAttribute(Qt.WA_StyledBackground,True);self.title.setObjectName('library_heading');self.title.setText(self.month.strftime('%B %Y'))
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);layout.addWidget(self.scroll,1)
        content=QWidget();self.grid=QGridLayout(content);self.grid.setSpacing(12);self.scroll.setWidget(content)
        self.finished.connect(self.stop);self.refresh_home_style();self.load()
    def refresh_home_style(self):
        from app.ui.theme_catalog import is_manga
        if is_manga():
            from app.ui.manga_style import library_qss
            self.setStyleSheet(library_qss())
        else:
            c=colors();self.setStyleSheet(f'QDialog{{background:{c["bg"]};color:{c["text"]};}} QLabel{{color:{c["text"]};}}')
    def change(self,delta):
        if not delta:self.month=date.today().replace(day=1)
        else:
            value=self.month.year*12+self.month.month-1+delta;self.month=date(value//12,value%12+1,1)
        self.load()
    def stop(self,*_):
        self.generation+=1
        if self.worker:self.worker.requestInterruption()
    def load(self):
        self.stop();generation=self.generation;first=self.month-timedelta(days=self.month.weekday());last=self.month.replace(day=calendar.monthrange(self.month.year,self.month.month)[1]);last+=timedelta(days=6-last.weekday())
        self.title.setText(self.month.strftime('%B %Y'));self.status.setText('Loading saved broadcasts…')
        from app.core.calendar_view import entries
        worker=IOTask(lambda:entries(first,last));self.worker=worker;track(worker)
        from app.ui.components.operation_progress import watch
        watch(self,worker,'Loading saved calendar broadcasts')
        def ready(rows):
            from PyQt5 import sip
            if not sip.isdeleted(self) and generation==self.generation:self.render(first,last,rows)
        def finished():
            from PyQt5 import sip
            if not sip.isdeleted(self) and self.worker is worker:self.worker=None
            worker.deleteLater()
        def failed(message):
            from PyQt5 import sip
            if not sip.isdeleted(self) and generation==self.generation:self.status.setText(message)
        worker.succeeded.connect(ready);worker.failed.connect(failed);worker.finished.connect(finished);worker.start()
    def render(self,first,last,rows):
        from app.ui.manga_pages import active
        from app.ui.components.home_day import HomeDay
        day_class=HomeDay if active() else AiringDay
        while self.grid.count():self.grid.takeAt(0).widget().deleteLater()
        for column,day in enumerate(calendar.day_abbr):self.grid.addWidget(QLabel(day),0,column);self.grid.setColumnStretch(column,1)
        for offset in range((last-first).days+1):
            current=first+timedelta(days=offset);items=[r for r in rows if date.fromtimestamp(r['airing_at'])==current]
            tile=day_class(current,current==date.today(),'月火水木金土日'[current.weekday()],items);tile.selected.connect(self.open_release);self.grid.addWidget(tile,offset//7+1,offset%7)
        self.status.setText(f'{len(rows)} saved broadcasts in this view · local time. Use Refresh and sync with internet to update cached schedules.')
    def open_release(self,release):
        parent=self.parentWidget()
        while parent:
            if hasattr(parent,'_open_airing_detail'):parent._open_airing_detail(release);return
            parent=parent.parentWidget()
