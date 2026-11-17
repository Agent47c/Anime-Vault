"""Shared staged genre/theme choices; apply once, never invent provider counts."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QWidget
from app.ui.components.tag_picker import TagPicker
from app.ui.components.flow_layout import FlowLayout


class TaxonomyPicker(TagPicker):
    def __init__(self,title,owner):self.owner=owner;super().__init__(title)
    def showPopup(self):
        self.dismiss_on_outside=True
        return super().showPopup()



class TaxonomyPanel(QFrame):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.setObjectName('transfer_panel');box=QVBoxLayout(self);box.setContentsMargins(20,16,20,16)
        heading=QLabel('Select Taxonomy & Tags');heading.setObjectName('workflow_row_title');box.addWidget(heading)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setMaximumHeight(260)
        content=QWidget();content.setObjectName('transfer_clear');columns=QHBoxLayout(content);self.groups=[]
        for picker in (owner.genre_filter,owner.theme_filter):
            column=QVBoxLayout();column.addWidget(QLabel(picker.title));surface=QWidget();surface.setObjectName('transfer_clear');flow=FlowLayout(surface);buttons=[]
            for index,(label,value) in enumerate(picker.items):
                if value is None:continue
                button=QPushButton(label);button.setCheckable(True);button.setChecked(index in picker.selected);button.setCursor(Qt.PointingHandCursor);button.setProperty('chip',True);button.setMinimumWidth(125);button.toggled.connect(self.count)
                flow.addWidget(button);buttons.append((index,button))
            column.addWidget(surface);column.addStretch();columns.addLayout(column,1);self.groups.append((picker,buttons))
        scroll.setWidget(content);box.addWidget(scroll)
        footer=QHBoxLayout();self.summary=QLabel();footer.addWidget(self.summary,1)
        clear=QPushButton('Clear tags');clear.clicked.connect(self.clear);footer.addWidget(clear)
        cancel=QPushButton('Cancel');cancel.clicked.connect(self.hide);footer.addWidget(cancel)
        apply=QPushButton('Apply filters');apply.setProperty('accent',True);apply.clicked.connect(self.apply);footer.addWidget(apply);box.addLayout(footer);self.count()
        for control in self.findChildren(QPushButton):control.setCursor(Qt.PointingHandCursor)
        from app.ui.manga_workflows import finish
        finish(self)
    def count(self,*_):
        if not hasattr(self,'summary'):return
        counts=[sum(button.isChecked() for _,button in buttons) for _,buttons in self.groups]
        self.summary.setText(f'{counts[0]} genres · {counts[1]} themes selected')
    def clear(self):
        for _,buttons in self.groups:
            for _,button in buttons:button.setChecked(False)
    def apply(self):
        for picker,buttons in self.groups:
            picker.blockSignals(True);picker._set_selected({index for index,button in buttons if button.isChecked()});picker.blockSignals(False)
        self.hide();self.owner.reset()
