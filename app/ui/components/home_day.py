"""Compact schedule tile with the existing hover preview and hover lift."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel,QProgressBar
from app.ui.components.airing_count import AiringDay
from app.ui.home_style import colors

class HomeDay(AiringDay):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.surface.glyph='';self.setFixedHeight(110);self.surface.setFixedHeight(102)
        self.count_label=QLabel(str(len(self.release_button.entries)));self.count_label.setObjectName('home_meta')
        self.surface.layout().itemAt(0).layout().addWidget(self.count_label)
        self.count_label.hide()
        entries=self.release_button.entries
        # Keep the release title/count on the same baseline in every day tile.
        self.release_button.layout().takeAt(0)
        self.release_button.layout().setAlignment(Qt.AlignVCenter)
        if len(entries)>1:
            title=self.release_button.findChild(QLabel,'airing_release_title')
            title.set_full_text(f'{len(entries)} anime releases')
            self.release_button.findChild(QLabel,'airing_release_time').setText('')
            self.release_button.findChild(QLabel,'airing_more').hide()
        self.transfer_label=QLabel();self.transfer_label.setObjectName('home_meta');self.transfer_label.hide()
        self.release_button.layout().addWidget(self.transfer_label)
        self.availability_bar=QProgressBar();self.availability_bar.setRange(0,1000);self.availability_bar.setTextVisible(False);self.availability_bar.setFixedHeight(3)
        self.surface.layout().addWidget(self.availability_bar);self.surface.layout().setSpacing(6)
        self.surface.setMinimumWidth(0)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.dot.hide()
    def download_state(self,label='',progress=None):
        more=self.release_button.findChild(QLabel,'airing_more')
        if more:more.hide()
        self.transfer_label.setVisible(bool(label));self.transfer_label.setText(label);self.transfer_label.setToolTip(label)
        self.availability_bar.setValue(round(progress*1000) if progress is not None else 0)
        self.availability_bar.setAccessibleName(label or 'No active transfer for this release')
