"""Explicit confirmation before applying multiple release selections."""
from PyQt5.QtCore import pyqtSignal,Qt
from PyQt5.QtGui import QImage,QPixmap
from PyQt5.QtWidgets import QHBoxLayout,QLabel,QCheckBox
from app.config import COVERS_DIR
from app.core import matching
from app.core.series_grouping import release_status
from app.ui.dialogs.drawer import DrawerDialog
from app.ui.components.workflow import chrome,card,text


def prepare(fid,selections):
    import copy
    result=matching.review_selection(fid,copy.deepcopy(selections));result['images']={}
    for media,_ in result['selections']:
        filename=media.get('_preview_cover')
        if filename:
            image=QImage(str(COVERS_DIR/filename))
            if not image.isNull():result['images'][media['id']]=image.scaled(44,66,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    return result


class MatchReview(DrawerDialog):
    confirmed=pyqtSignal(object)
    def __init__(self,prepared,parent=None):
        super().__init__(parent);self.prepared=prepared
        from app.core.anilist_client import resolve_display_title
        body,self.apply_button=chrome(self,'Confirm selected seasons','These releases will appear together under one anime card.','照合','Confirm matches',self.apply)
        body.addWidget(text('Main series: '+resolve_display_title(prepared['root']),'workflow_row_title'))
        for media,sid in prepared['selections']:
            frame,labels=card();line=QHBoxLayout()
            image=prepared['images'].get(media['id'])
            if image is not None:
                poster=QLabel();poster.setPixmap(QPixmap.fromImage(image));poster.setAccessibleName('Poster for '+resolve_display_title(media));line.addWidget(poster)
            line.addWidget(text(resolve_display_title(media),'workflow_row_title'),1);labels.addLayout(line)
            labels.addWidget(text(release_status(media.get('status'))))
            local=prepared['seasons'].get(sid)
            labels.addWidget(text(('Local season '+str(local['season_number'])+' · '+(local.get('season_folder_path') or local['title_display'])) if local else 'Metadata only · No local folder assigned'))
            body.addWidget(frame)
        body.addWidget(text('Existing paths, files, episode history, notes and ratings are kept. Announced releases are shown as not released, not as missing downloads.'))
        self.reviewed=QCheckBox('I reviewed the releases and local season assignments');body.addWidget(self.reviewed)
        self.apply_button.setEnabled(False);self.reviewed.toggled.connect(self.apply_button.setEnabled)
        body.addStretch()
    def apply(self):
        if self.reviewed.isChecked():self.confirmed.emit(self.prepared['selections']);self.accept()
