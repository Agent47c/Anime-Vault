"""Light master hero using the existing resume, artwork and playback behavior."""
from app.ui.manga_style import set_material
from PyQt5.QtCore import Qt,QRectF,QEvent
from PyQt5.QtGui import QPainter,QPainterPath,QColor,QLinearGradient,QIcon
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar
from app.ui.components.home_hero import HomeHero
from app.ui.components.design import ElidedLabel
from app.ui.manga_style import controls_qss,shadow,COLORS
from app.ui.icons import icon
from app.ui.home_style import px


class SegmentedProgress(QProgressBar):
    """Master's inset segments, driven by actual playback time rather than guesses."""
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        from app.ui.manga_style import manga_colors
        colors=manga_colors()
        rect=QRectF(self.rect()).adjusted(1,1,-1,-1);painter.setPen(Qt.NoPen);painter.setBrush(QColor(colors.get('inset','#c9cfdb')));painter.drawRoundedRect(rect,4,4)
        span=max(1,self.maximum()-self.minimum());fraction=max(0,min(1,(self.value()-self.minimum())/span))
        width=(rect.width()-6-12*5)/13
        for i in range(13):
            cell=QRectF(rect.left()+3+i*(width+5),rect.top()+2,width,max(1,rect.height()-4));painter.setBrush(QColor(colors['raised'] if 'inset' in colors else '#dfe3eb'));painter.drawRoundedRect(cell,3,3)
            fill=max(0,min(1,fraction*13-i))
            if fill:painter.setBrush(QColor('#ff2e93'));painter.drawRoundedRect(QRectF(cell.left(),cell.top(),cell.width()*fill,cell.height()),3,3)


class WrappedTitle(QLabel):
    def set_full_text(self,value):
        self._full_text=value;self.setToolTip(value);self.setAccessibleName(value);self._fit_text()
    def _fit_text(self):
        if not hasattr(self,'_full_text') or getattr(self,'_fitting',False):return
        self._fitting=True
        try:
            words=self._full_text.split();lines=[];metrics=self.fontMetrics();width=max(1,self.width())
            for _ in range(2):
                line=[]
                while words and (not line or metrics.horizontalAdvance(' '.join(line+[words[0]]))<=width):line.append(words.pop(0))
                lines.append(' '.join(line))
                if not words:break
            if words:lines.append(metrics.elidedText(' '.join(words),Qt.ElideRight,width))
            self.setText('\n'.join(lines))
        finally:self._fitting=False
    def resizeEvent(self,event):super().resizeEvent(event);self._fit_text()
    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type()==QEvent.FontChange:self._fit_text()


class MangaHero(HomeHero):
    def __init__(self,parent=None):
        # Qt cannot reliably compose a parent graphics effect with animated
        # effects on its buttons: child text can disappear from the source.
        super().__init__(parent);self.setFixedHeight(px(420))
    def _setup_ui(self):
        self.setObjectName('manga_hero');box=QVBoxLayout(self);box.setContentsMargins(38,30,38,32);box.setSpacing(15)
        self.eyebrow=QLabel('●  CONTINUE WATCHING');box.addWidget(self.eyebrow,0,Qt.AlignLeft);box.addSpacing(9)
        self.title_label=WrappedTitle('Anime Vault');self.title_label.setWordWrap(True);self.title_label.setMaximumWidth(820);box.addWidget(self.title_label)
        self.sub_label=ElidedLabel('');self.sub_label.setMaximumWidth(800);box.addWidget(self.sub_label)
        self.playback_bar=SegmentedProgress();self.playback_bar.setFixedSize(390,17);self.playback_bar.setTextVisible(False);self.playback_bar.setRange(0,1000);box.addWidget(self.playback_bar)
        self.playback_text=QLabel();box.addWidget(self.playback_text);box.addStretch()
        row=QHBoxLayout();row.setSpacing(14)
        self.resume_btn=QPushButton('Resume episode');self.resume_btn.setProperty('accent',True);self.resume_btn.clicked.connect(self._on_resume)
        self.details_btn=QPushButton('Series Details');self.details_btn.clicked.connect(self._on_details)
        self.folder_btn=QPushButton();self.folder_btn.setIcon(icon('organizer',COLORS['text']));self.folder_btn.setFixedWidth(54);self.folder_btn.setAccessibleName('Open anime folder');self.folder_btn.clicked.connect(self.open_folder)
        from app.ui.components.neumorphic import install
        for button in (self.resume_btn,self.details_btn,self.folder_btn):button.setCursor(Qt.PointingHandCursor);button.setMinimumHeight(52);row.addWidget(button);install(button)
        row.addStretch();box.addLayout(row);self.offline_badge=QLabel(self);self.offline_badge.hide();self.refresh_style();self.update_playback({})
    def refresh_style(self):
        from app.ui.manga_style import manga_colors
        from app.ui.theme_catalog import is_manga_dark
        colors=manga_colors()
        self.setFixedHeight(px(420))
        self.setProperty('animevaultOwnScaledStyle',True);set_material(self,controls_qss()+'QWidget#manga_hero QLabel{background:transparent;}')
        set_material(self.title_label,f'color:#111217;font-family:"Noto Serif";font-size:{px(40)}px;font-weight:800;')
        self.title_label.setMaximumHeight(px(190))
        set_material(self.eyebrow,'background:white;color:#111217;border-radius:6px;padding:7px 12px;font:600 12px Inter;')
        set_material(self.sub_label,'color:#535b6d;font:13px "JetBrains Mono";');set_material(self.playback_text,'color:#535b6d;font:12px "JetBrains Mono";')
        set_material(self.playback_bar,'QProgressBar{background:#d0d5df;border:1px solid white;border-radius:4px;}QProgressBar::chunk{background:#ff2e93;border-radius:3px;}')
        self.resume_btn.setIcon(icon('play',COLORS['text']));self.resume_btn.setMinimumWidth(240);self.details_btn.setMinimumWidth(180)
        self.folder_btn.setIcon(icon('organizer',colors['text']))
        self.details_btn.setIcon(icon('info',colors['text']) if is_manga_dark() else QIcon())
    def open_folder(self):
        parent=self.parentWidget()
        while parent:
            if hasattr(parent,'_open_library_action') and self.current_fid:
                parent._open_library_action(self.current_fid,'folder');return
            parent=parent.parentWidget()
    def paintEvent(self,event):
        from app.ui.manga_style import manga_colors
        from app.ui.theme_catalog import is_manga_dark
        colors=manga_colors();dark=is_manga_dark()
        canvas=QColor(colors['bg'])
        def tint(alpha):
            color=QColor(canvas);color.setAlpha(alpha);return color
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);clip=QPainterPath();clip.addRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),25,25);p.setClipPath(clip);p.fillRect(self.rect(),canvas)
        w,h=self.width(),self.height()
        if not self._banner.isNull():
            if self._scaled_banner_size!=(w,h):self._scaled_banner=self._banner.scaled(w,h,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);self._scaled_banner_size=(w,h)
            p.drawPixmap((w-self._scaled_banner.width())//2,(h-self._scaled_banner.height())//2,self._scaled_banner)
            p.fillRect(self.rect(),QColor(0,0,0,45 if dark else 8))
        shade=QLinearGradient(0,0,w,0);shade.setColorAt(0,canvas);shade.setColorAt(.46,tint(205 if dark else 170));shade.setColorAt(1,tint(8));p.fillRect(self.rect(),shade)
        bottom=QLinearGradient(0,0,0,h);bottom.setColorAt(0,tint(0));bottom.setColorAt(1,tint(215 if dark else 125));p.fillRect(self.rect(),bottom)
        p.setClipping(False);p.setPen(QColor(colors['line'] if dark else '#ffffff'));p.setBrush(Qt.NoBrush);p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),25,25)
