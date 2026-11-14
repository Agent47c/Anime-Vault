"""Shared human-readable transfer limits; stored values remain KiB/second."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QLineEdit,QLabel


def rate_label(value):
    if not value:return 'Unlimited'
    return f'{value/1024:g} MB/s' if value>=1024 and value%512==0 else f'{value:,} KB/s'


class RateLimitPicker(QWidget):
    valueChanged=pyqtSignal(int)
    def __init__(self,parent=None):
        super().__init__(parent)
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(8)
        self.presets=QComboBox();self.presets.setMinimumHeight(44)
        self.presets.addItem('Unlimited',0)
        for value in range(512,10241,512):self.presets.addItem(rate_label(value),value)
        self.presets.addItem('Custom…',None);box.addWidget(self.presets)
        self.custom_row=QWidget();row=QHBoxLayout(self.custom_row);row.setContentsMargins(0,0,0,0)
        self.custom=QLineEdit('512');self.custom.setValidator(QIntValidator(0,1000000,self));self.custom.setPlaceholderText('e.g. 15 or 2000');self.custom.setMinimumHeight(44)
        self.custom.setAccessibleName('Custom transfer limit in KB per second')
        row.addWidget(self.custom,1);row.addWidget(QLabel('KB/s'));box.addWidget(self.custom_row);self.custom_row.hide()
        self.setToolTip('0 means unlimited. 1 KB = 1,024 bytes; 1 MB = 1,024 KB.')
        self.presets.currentIndexChanged.connect(self._changed);self.custom.textEdited.connect(self._changed)
    def value(self):
        value=self.presets.currentData()
        if value is not None:return value
        text=self.custom.text().strip()
        if not text or not text.isdigit() or not 0<=int(text)<=1000000:raise ValueError('Enter a custom limit from 0 to 1,000,000 KB/s.')
        return int(text)
    def setValue(self,value):
        value=int(value)
        if not 0<=value<=1000000:raise ValueError('Transfer limit is out of range.')
        index=self.presets.findData(value)
        self.presets.blockSignals(True);self.custom.setText(str(value));self.presets.setCurrentIndex(index if index>=0 else self.presets.count()-1);self.presets.blockSignals(False)
        self.custom_row.setVisible(index<0)
    def _changed(self,*_):
        self.custom_row.setVisible(self.presets.currentData() is None)
        try:self.valueChanged.emit(self.value())
        except ValueError:pass
