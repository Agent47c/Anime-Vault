"""Cinematic Home hero, backed by the existing resume/details actions."""
from PyQt5.QtCore import Qt,QRectF
from PyQt5.QtGui import QPainter,QPainterPath,QColor,QLinearGradient,QPixmap
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar
from app.ui.pages.library_page import HeroResumeCard
from app.ui.components.design import ElidedLabel
from app.ui.home_style import colors,px
from app.core.parser import extract_episode_numbers
from pathlib import Path
from PyQt5.QtWidgets import QSizePolicy
from app.ui.icons import icon


class HomeHero(HeroResumeCard):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedHeight(260)
    def _setup_ui(self):
        self.setObjectName('home_hero');box=QVBoxLayout(self);box.setContentsMargins(24,24,24,24);box.setSpacing(8);box.addStretch()
        self.eyebrow=QLabel('CONTINUE WATCHING');self.eyebrow.setObjectName('home_eyebrow');box.addWidget(self.eyebrow)
        bottom=QHBoxLayout();bottom.setSpacing(24);left=QVBoxLayout();left.setSpacing(7)
        self.title_label=ElidedLabel('Anime Vault');self.title_label.setStyleSheet('color:#f5f3f8;font-family:"Plus Jakarta Sans";font-size:28px;font-weight:700;')
        left.addWidget(self.title_label)
        self.sub_label=ElidedLabel('');self.sub_label.setStyleSheet('color:#c9c3df;font-family:"JetBrains Mono";font-size:11px;');left.addWidget(self.sub_label)
        self.playback_text=QLabel();self.playback_text.setStyleSheet('color:#c9c3df;font-family:"JetBrains Mono";font-size:11px;');left.addWidget(self.playback_text)
        self.playback_bar=QProgressBar();self.playback_bar.setRange(0,1000);self.playback_bar.setTextVisible(False);self.playback_bar.setFixedHeight(4);self.playback_bar.setMaximumWidth(450)
        progress_row=QHBoxLayout();progress_row.addWidget(self.playback_bar);progress_row.addStretch();left.addLayout(progress_row)
        bottom.addLayout(left,1)
        self.resume_btn=QPushButton('Resume episode');self.resume_btn.setObjectName('home_resume');self.resume_btn.setMinimumHeight(44);self.resume_btn.setCursor(Qt.PointingHandCursor);self.resume_btn.clicked.connect(self._on_resume)
        self.details_btn=QPushButton('Series Details');self.details_btn.setObjectName('home_details');self.details_btn.setMinimumHeight(44);self.details_btn.setCursor(Qt.PointingHandCursor);self.details_btn.clicked.connect(self._on_details)
        bottom.addWidget(self.resume_btn,0,Qt.AlignBottom);bottom.addWidget(self.details_btn,0,Qt.AlignBottom);box.addLayout(bottom)
        self.offline_badge=QLabel(self);self.offline_badge.hide();self.update_playback({});self.refresh_style()
    def refresh_style(self):
        c=colors();self.eyebrow.setStyleSheet(f'color:{c["coral"]};font-family:"JetBrains Mono";font-size:{px(11)}px;font-weight:600;')
        for label in (self.eyebrow,self.title_label,self.sub_label,self.playback_text):label.setProperty('animevaultOwnScaledStyle',True)
        self.title_label.setStyleSheet(f'color:#f5f3f8;font-family:"Plus Jakarta Sans";font-size:{px(28)}px;font-weight:700;')
        for label in (self.sub_label,self.playback_text):label.setStyleSheet(f'color:#c9c3df;font-family:"JetBrains Mono";font-size:{px(11)}px;')
        self.resume_btn.setProperty('animevaultOwnScaledStyle',True);self.details_btn.setProperty('animevaultOwnScaledStyle',True)
        self.resume_btn.setStyleSheet(f'QPushButton#home_resume{{background:{c["coral"]};color:{c["on_coral"]};border:none;border-radius:22px;min-height:44px;padding:0 22px;font-size:15px;font-weight:600;}} QPushButton#home_resume:hover{{background:#ff8ba2;color:#15131e;}} QPushButton#home_resume:disabled{{background:#50434c;color:#c9c3df;}}')
        self.details_btn.setStyleSheet('QPushButton#home_details{background:#2b2834;color:#f5f3f8;border:1px solid #353047;border-radius:22px;min-height:44px;padding:0 18px;} QPushButton#home_details:hover{background:#3a3744;}')
        self.resume_btn.setMaximumWidth(px(250));self.details_btn.setMaximumWidth(px(160))
        self.resume_btn.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed);self.details_btn.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
        self.resume_btn.setIcon(icon('play',c['on_coral']))
        self.playback_bar.setStyleSheet(f'QProgressBar{{background:#36333f;border:none;border-radius:2px;}} QProgressBar::chunk{{background:{c["coral"]};border-radius:2px;}}')
    def refresh(self):
        super().refresh()
        episode=getattr(self,'_resume_episode',None);numbers=extract_episode_numbers(Path(episode).name) if episode else []
        if episode:self.resume_btn.setText(('Resume Episode ' if 'Resume' in self.resume_btn.text() else 'Play Episode ')+(str(numbers[0]) if numbers else ''))
        if getattr(self,'_live_playback',{}).get('path')!=episode:self.update_playback({})
    def present_session(self,record,path,banner=None,available=True):
        self.current_fid=record['id'];self._resume_episode=path;self.title_label.set_full_text(record.get('display_title') or 'Anime')
        numbers=extract_episode_numbers(Path(path).name);self.sub_label.set_full_text(('Episode '+str(numbers[0])+' · ' if numbers else '')+Path(path).stem)
        self.resume_btn.setText(('Resume Episode '+str(numbers[0]) if numbers else 'Resume episode') if available else 'Episode unavailable locally');self.resume_btn.setEnabled(available)
        if banner is not None:
            self._banner=QPixmap.fromImage(banner);self._scaled_banner_size=None;self.update()
        self.show()
    def update_playback(self,state):
        self._live_playback=state
        if state.get('active'):
            numbers=extract_episode_numbers(Path(state.get('path') or '').name)
            self.resume_btn.setText(('Resume' if state.get('paused') else 'Pause')+(' Episode '+str(numbers[0]) if numbers else ' episode'))
        self.resume_btn.setIcon(icon('pause' if state.get('active') and not state.get('paused') else 'play',colors()['on_coral']))
        duration=state.get('duration',0);position=state.get('position',0)
        if not state.get('active') and self.resume_btn.isEnabled() and getattr(self,'_resume_episode',None):
            numbers=extract_episode_numbers(Path(self._resume_episode).name)
            self.resume_btn.setText(('Play' if duration and position>=duration*.95 else 'Resume')+(' Episode '+str(numbers[0]) if numbers else ' episode'))
        self.playback_bar.setVisible(bool(duration));self.playback_bar.setValue(round(min(1,position/duration)*1000) if duration else 0)
        if duration:
            remaining=max(0,duration-position)
            self.playback_text.setText(f'{int(remaining//60):02d}:{int(remaining%60):02d} left of {int(duration//60):02d}:{int(duration%60):02d}')
            self.playback_text.setToolTip('Saved playback position'+(' · Player connected' if state.get('active') else ''))
        else:
            self.playback_text.setText('Playback progress not available yet');self.playback_text.setToolTip('Live progress and Space play/pause work with app-launched VLC or MPV.')
        self.playback_bar.setAccessibleName(f'{round(position)} of {round(duration)} seconds played' if duration else 'Playback progress unavailable')
    def _on_resume(self):
        state=getattr(self,'_live_playback',{})
        if state.get('active'):
            from app.ui.playback import monitor
            monitor().toggle()
        else:super()._on_resume()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);clip=QPainterPath();clip.addRoundedRect(QRectF(self.rect()),12,12);p.setClipPath(clip)
        p.fillRect(self.rect(),QColor('#201821'));w,h=self.width(),self.height()
        if not self._banner.isNull():
            if self._scaled_banner_size!=(w,h):self._scaled_banner=self._banner.scaled(w,h,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);self._scaled_banner_size=(w,h)
            p.drawPixmap((w-self._scaled_banner.width())//2,(h-self._scaled_banner.height())//2,self._scaled_banner)
        p.fillRect(self.rect(),QColor(20,18,29,100))
        shade=QLinearGradient(0,0,0,h);shade.setColorAt(0,QColor(20,18,29,30));shade.setColorAt(.4,QColor(20,18,29,100));shade.setColorAt(1,QColor('#14121d'));p.fillRect(self.rect(),shade)
        side=QLinearGradient(0,0,w,0);side.setColorAt(0,QColor(20,18,29,125));side.setColorAt(1,QColor(20,18,29,0));p.fillRect(self.rect(),side)
