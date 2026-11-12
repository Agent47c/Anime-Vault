"""One painted queue row; no persistent widgets per torrent."""
from PyQt5.QtCore import Qt,QRect,QEvent,pyqtSignal,QPoint
from PyQt5.QtGui import QColor,QPen,QFont
from PyQt5.QtWidgets import QStyledItemDelegate,QStyle
from app.ui.home_style import colors,px
from app.ui.icons import icon
from app.core import download_queue
from app.core.storage import format_bytes

def action_rects(rect):
    return [QRect(rect.right()-px(126-i*40),rect.top()+px(16),px(34),px(34)) for i in range(3)]

class TransferDelegate(QStyledItemDelegate):
    action_requested=pyqtSignal(int,int,QPoint)
    def editorEvent(self,event,model,option,index):
        if event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton:
            for number,button in enumerate(action_rects(option.rect.adjusted(0,4,-2,-4))):
                if button.contains(event.pos()):
                    self.action_requested.emit(index.row(),number,event.pos());return True
        return super().editorEvent(event,model,option,index)
    def paint(self,painter,option,index):
        item=index.data(Qt.UserRole);c=colors();state=download_queue.status(item)
        tint=c['ok'] if state=='Completed' else c['amber'] if state in ('Paused','Stopped') else c['coral']
        painter.save();painter.setRenderHint(painter.Antialiasing);rect=option.rect.adjusted(0,4,-2,-4)
        painter.setPen(QPen(QColor(c['coral'] if option.state&QStyle.State_Selected else c['panel']),1));painter.setBrush(QColor(c['panel']));painter.drawRoundedRect(rect,12,12)
        icon('downloads' if state!='Completed' else 'check',tint).paint(painter,QRect(rect.left()+px(18),rect.top()+px(22),px(22),px(22)))
        actions=action_rects(rect);x=rect.left()+px(60);width=max(10,actions[0].left()-x-px(10))
        font=QFont('Plus Jakarta Sans');font.setPixelSize(px(13));font.setBold(True);painter.setFont(font);painter.setPen(QColor(c['text']))
        title=item.get('release_title') or item['title'];painter.drawText(x,rect.top()+px(29),painter.fontMetrics().elidedText(title,Qt.ElideRight,width))
        font.setFamily('JetBrains Mono');font.setPixelSize(px(10));font.setBold(False);painter.setFont(font);painter.setPen(QColor(c['muted']))
        eta=item.get('eta');eta=f'{eta//60}m {eta%60}s' if isinstance(eta,int) and 0<=eta<8640000 else '—'
        from app.core.download_discovery import coverage_label
        coverage=coverage_label(item.get('episode_keys') or [])
        detail=f"{state} · {coverage} · {format_bytes(item.get('downloaded') or 0)} / {format_bytes(item.get('total') or 0)} · {format_bytes(item.get('download_rate') or 0)}/s · ETA {eta}"
        painter.drawText(x,rect.top()+px(49),painter.fontMetrics().elidedText(detail,Qt.ElideRight,width))
        for button,name in zip(actions,('organizer' if state=='Completed' else 'play' if state in ('Paused','Stopped','Failed') else 'pause','list','more')):
            painter.setBrush(QColor(c['raised']));painter.setPen(Qt.NoPen);painter.drawEllipse(button);icon(name,c['muted']).paint(painter,button.adjusted(px(9),px(9),-px(9),-px(9)))
        track=QRect(rect.left()+px(16),rect.bottom()-px(18),rect.width()-px(70),px(5));painter.setBrush(QColor(c['line']));painter.drawRoundedRect(track,2,2)
        fill=QRect(track);fill.setWidth(round(track.width()*max(0,min(1,item.get('progress') or 0))));painter.setBrush(QColor(tint));painter.drawRoundedRect(fill,2,2)
        painter.setPen(QColor(tint));painter.drawText(QRect(track.right()+px(6),track.top()-px(5),px(40),px(18)),Qt.AlignCenter,f"{item.get('progress',0):.0%}")
        painter.restore()
