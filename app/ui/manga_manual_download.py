"""Apply only Search & Auto Ingest, reusing the existing submission controls."""
from PyQt5.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QPushButton,QLabel
from app.ui.components.workflow import field

def configure(dialog,body):
    from app.ui.manga_pages import active
    if not active():return
    dialog.setObjectName('manual_ingest');dialog.centered_workflow=True;dialog.workflow_width=850
    dialog.findChild(QLabel,'workflow_title').setText('Add magnet or torrent')
    header=dialog.findChild(QWidget,'workflow_header')
    if header:header.findChild(QLabel,'workflow_hint').setText('Search your source website, or paste a magnet link / choose a torrent file.')
    dialog.timer.stop()
    # Retain configuration widgets and their values for _config(); their full
    # interface remains in Settings. Only the requested ingest section is shown.
    dialog._ingest_configuration=QWidget(dialog);dialog._ingest_configuration.hide()
    dialog._ingest_configuration.setFixedSize(0,0)
    while body.count():
        item=body.takeAt(0)
        if item.widget():item.widget().setParent(dialog._ingest_configuration)
    panel=QFrame();panel.setObjectName('transfer_panel');box=QVBoxLayout(panel);box.setContentsMargins(20,20,20,20);box.setSpacing(16)
    header=QHBoxLayout();header.addWidget(QLabel('Search & Auto Ingest'),1);header.addWidget(dialog.seed);dialog.seed.show();box.addLayout(header)
    row=QHBoxLayout();left=QVBoxLayout();right=QVBoxLayout();field(left,'Search title',dialog.query_title);field(right,'Season folder',dialog.season);row.addLayout(left,2);row.addLayout(right,1);box.addLayout(row)
    field(box,'Episode targeting',dialog.episode)
    field(box,'Website search URL template',dialog.controls['source'])
    row=QHBoxLayout()
    for key,label in (('group','Release group (optional)'),('quality','Quality profile (optional)')):
        column=QVBoxLayout();field(column,label,dialog.controls[key]);row.addLayout(column)
    box.addLayout(row)
    search=QPushButton('Search website');search.setProperty('accent',True);search.clicked.connect(dialog._search);box.addWidget(search)
    box.addWidget(QLabel('Or manual torrent entry'))
    row=QHBoxLayout();row.addWidget(dialog.source,1);choose=QPushButton('Choose .torrent file…');choose.clicked.connect(dialog._browse_torrent);row.addWidget(choose);row.addWidget(dialog.add_button);box.addLayout(row)
    box.addWidget(dialog.status);dialog.status.show();body.addWidget(panel);body.addStretch()
    dialog.save_button.hide()
    for control in (dialog.query_title,dialog.season,dialog.episode,dialog.source,dialog.add_button,*[dialog.controls[k] for k in ('source','group','quality')]):control.show()
    from app.ui.manga_additional import qss
    dialog.setStyleSheet(qss('manual_ingest'))
    dialog._ingest_configuration.hide()
    dialog.list.hide();dialog.list.setFixedSize(0,0)
