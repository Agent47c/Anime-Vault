"""One theme-aware presentation for existing Qt alerts and confirmations.

Keep Qt's button identities, roles, return values and keyboard behaviour.
Native message-box buttons deliberately avoid graphics-effect source capture.
"""
from PyQt5.QtCore import QObject,QEvent,Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox,QPushButton,QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QDialogButtonBox,QApplication,QPlainTextEdit
from app.ui.home_style import colors,px


class MessageBoxes(QObject):
    def __init__(self,app):
        super().__init__(app);self.busy=False

    def apply(self,box):
        if self.busy:return
        self.busy=True
        try:
            c=colors();box.setProperty('animevaultOwnScaledStyle',True)
            danger_color = '#ff746d' if QColor(c['panel']).lightness() < 128 else '#b3261e'
            if QApplication.instance().property('animevaultHighContrast'):
                danger_color = c['text']
            selector='QWidget#app_message_box' if box.property('stableAlert') else 'QMessageBox'
            box.setStyleSheet(f'''
                {selector} {{background:{c['bg']};color:{c['text']};}}
                {selector} QLabel {{background:transparent;color:{c['text']};border:none;font-size:{px(14)}px;}}
                {selector} QDialogButtonBox {{background:transparent;border:none;}}
                {selector} QCheckBox {{background:transparent;color:{c['text']};spacing:10px;min-height:{px(32)}px;}}
                {selector} QCheckBox::indicator {{width:20px;height:20px;border:2px solid {c['muted']};border-radius:4px;background:{c['panel']};}}
                {selector} QCheckBox::indicator:checked {{background:{c['coral']};border-color:{c['coral']};}}
            ''')
            for button in box.findChildren(QPushButton):
                role=box.buttonRole(button)
                primary=role in (QMessageBox.AcceptRole,QMessageBox.YesRole)
                danger=role==QMessageBox.DestructiveRole
                face=c['coral'] if primary else c['panel']
                ink=c['on_coral'] if primary else danger_color if danger else c['text']
                border=danger_color if danger else c['coral'] if primary else c['line']
                button.setGraphicsEffect(None)
                button.setCursor(Qt.PointingHandCursor)
                button.setStyleSheet(f'''
                    QPushButton {{background:{face};color:{ink};border:1px solid {border};border-radius:8px;padding:0 {px(18)}px;font-size:{px(13)}px;font-weight:600;}}
                    QPushButton:hover {{background:{face if primary else c['raised']};color:{ink};border-color:{border};}}
                    QPushButton:pressed {{background:{face if primary else c['raised']};color:{ink};border:2px solid {border};}}
                    QPushButton:focus {{border:2px solid {border};outline:none;}}
                    QPushButton:disabled {{color:{c['muted']};background:{c['raised']};}}
                ''')
                button.ensurePolished()
                caption_width = button.fontMetrics().horizontalAdvance(button.text())
                button.setMinimumSize(max(px(96), caption_width + 2 * px(18) + 4), px(42))
        finally:self.busy=False

    def eventFilter(self,obj,event):
        if isinstance(obj,QMessageBox) and event.type() in (QEvent.Polish,QEvent.Show):self.apply(obj)
        return False


def install(app):
    if not hasattr(app,'_message_boxes'):
        app._message_boxes=MessageBoxes(app);app.installEventFilter(app._message_boxes)
    for widget in app.topLevelWidgets():
        if isinstance(widget,QMessageBox) or widget.property('stableAlert'):app._message_boxes.apply(widget)


class AppMessageBox(QDialog):
    """Reusable app alert with the standard QMessageBox call/return contract."""
    def __init__(self,icon=None,title='',text='',buttons=QMessageBox.NoButton,parent=None):
        if isinstance(icon,QWidget):parent,icon=icon,None
        super().__init__(parent)
        self.setObjectName('app_message_box');self.setProperty('stableAlert',True)
        self.setModal(True);self.setWindowTitle(title);self._clicked=None;self._roles={};self._standards={}
        body=QVBoxLayout(self);body.setContentsMargins(24,24,24,24);body.setSpacing(18)
        header=QHBoxLayout();body.addLayout(header)
        self.symbol=QLabel('!' if icon in (QMessageBox.Warning,QMessageBox.Critical) else '?' if icon==QMessageBox.Question else 'i')
        self.symbol.setAlignment(Qt.AlignCenter);self.symbol.setFixedSize(32,32);header.addWidget(self.symbol)
        self.heading=QLabel(title);self.heading.setTextFormat(Qt.PlainText);self.heading.setWordWrap(True);header.addWidget(self.heading,1)
        self.message=QLabel();self.message.setTextFormat(Qt.PlainText);self.message.setWordWrap(True);body.addWidget(self.message)
        self.information_label=QLabel();self.information_label.setTextFormat(Qt.PlainText);self.information_label.setWordWrap(True);self.information_label.hide();body.addWidget(self.information_label)
        self.actions=QDialogButtonBox();body.addWidget(self.actions);self.setText(text)
        self.setMinimumWidth(440);self.setMaximumWidth(760)
        if buttons:self.setStandardButtons(buttons)

    def setWindowTitle(self,title):
        super().setWindowTitle(title)
        if hasattr(self,'heading'):self.heading.setText(title)
    def setText(self,value):self.message.setText(value)
    def text(self):return self.message.text()
    def setInformativeText(self,value):self.information_label.setText(value);self.information_label.setVisible(bool(value))
    def informativeText(self):return self.information_label.text()
    def setCheckBox(self,checkbox):
        self._checkbox=checkbox;self.layout().insertWidget(self.layout().indexOf(self.actions),checkbox)
    def checkBox(self):return getattr(self,'_checkbox',None)
    def setDetailedText(self,value):
        if not hasattr(self,'details'):
            self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(220);self.details.hide()
            self.layout().insertWidget(self.layout().indexOf(self.actions),self.details)
            self.details_button=QPushButton('Show details')
            self.actions.addButton(self.details_button,QDialogButtonBox.ActionRole)
            self.details_button.clicked.connect(self._toggle_details)
        self.details.setPlainText(value);self.details_button.setVisible(bool(value))
    def detailedText(self):return self.details.toPlainText() if hasattr(self,'details') else ''
    def _toggle_details(self):
        show=self.details.isHidden();self.details.setVisible(show);self.details_button.setText('Hide details' if show else 'Show details');self.adjustSize()
    def addButton(self,value,role=None):
        if role is None:
            standard=value
            button=self.actions.addButton(QDialogButtonBox.StandardButton(int(standard)))
            self._standards[standard]=button;role=int(self.actions.buttonRole(button))
        else:
            button=value if isinstance(value,QPushButton) else QPushButton(value)
            self.actions.addButton(button,QDialogButtonBox.ButtonRole(int(role)))
        self._roles[button]=role;button.clicked.connect(lambda checked=False,b=button:self._choose(b))
        return button
    def setStandardButtons(self,buttons):
        for standard in (QMessageBox.Ok,QMessageBox.Yes,QMessageBox.No,QMessageBox.Cancel,QMessageBox.Close,QMessageBox.Retry,QMessageBox.Abort,QMessageBox.Ignore,QMessageBox.Save,QMessageBox.Discard):
            if buttons & standard and standard not in self._standards:self.addButton(standard)
    def button(self,standard):return self._standards.get(standard)
    def buttons(self):return self.actions.buttons()
    def buttonRole(self,button):return self._roles.get(button,QMessageBox.InvalidRole)
    def clickedButton(self):return self._clicked
    def setDefaultButton(self,value):
        button=self.button(value) if not isinstance(value,QPushButton) else value
        if button:button.setDefault(True);button.setFocus()
    def defaultButton(self):return next((b for b in self.buttons() if b.isDefault()),None)
    def _choose(self,button):
        self._clicked=button
        result=next((int(k) for k,v in self._standards.items() if v is button),int(QMessageBox.Accepted) if self.buttonRole(button)==QMessageBox.AcceptRole else int(QMessageBox.Rejected))
        self.done(result)
    def reject(self):
        button=self.button(QMessageBox.Cancel) or self.button(QMessageBox.No) or self.button(QMessageBox.Close)
        if button:self._choose(button)
        else:super().reject()
    def refresh_home_style(self):
        app=QApplication.instance();install(app);app._message_boxes.apply(self)
        c=colors();self.heading.setStyleSheet(f'font-size:{px(20)}px;font-weight:700;background:transparent;color:{c["text"]};')
        self.symbol.setStyleSheet(f'background:{c["raised"]};color:{c["coral"]};border:1px solid {c["coral"]};border-radius:16px;font-size:20px;font-weight:700;')
        if hasattr(self,'details'):self.details.setStyleSheet(f'background:{c["panel"]};color:{c["text"]};border:1px solid {c["line"]};border-radius:8px;padding:8px;')
    def showEvent(self,event):
        self.refresh_home_style();super().showEvent(event)
    @classmethod
    def _show(cls,kind,parent,title,text,buttons,default):
        box=cls(kind,title,text,buttons,parent)
        if default:box.setDefaultButton(default)
        elif kind==QMessageBox.Question:box.setDefaultButton(QMessageBox.No)
        result=box.exec_();box.deleteLater();return result
    @classmethod
    def warning(cls,parent,title,text,buttons=QMessageBox.Ok,default=QMessageBox.NoButton):return cls._show(QMessageBox.Warning,parent,title,text,buttons,default)
    @classmethod
    def information(cls,parent,title,text,buttons=QMessageBox.Ok,default=QMessageBox.NoButton):return cls._show(QMessageBox.Information,parent,title,text,buttons,default)
    @classmethod
    def critical(cls,parent,title,text,buttons=QMessageBox.Ok,default=QMessageBox.NoButton):return cls._show(QMessageBox.Critical,parent,title,text,buttons,default)
    @classmethod
    def question(cls,parent,title,text,buttons=QMessageBox.Yes|QMessageBox.No,default=QMessageBox.NoButton):return cls._show(QMessageBox.Question,parent,title,text,buttons,default)


for _name in ('NoButton','Ok','Yes','No','Cancel','Close','Retry','Abort','Ignore','Save','Discard','AcceptRole','RejectRole','DestructiveRole','YesRole','NoRole','InvalidRole','Warning','Critical','Information','Question'):
    setattr(AppMessageBox,_name,getattr(QMessageBox,_name))
