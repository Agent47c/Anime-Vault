"""Twilight Sakura release search presentation; no download decisions live here."""
from PyQt5.QtCore import Qt,QRectF,QSize,QEvent
from PyQt5.QtGui import QColor,QPainter,QPen,QFont
from PyQt5.QtWidgets import QStyledItemDelegate,QStyle,QCheckBox
from app.ui.home_style import colors,px
from app.ui.transfer_style import qss as transfer_qss
from app.ui.button_system import unified


@unified('QWidget#release_search_page')
def qss():
    c=colors();r='QWidget#release_search_page'
    return transfer_qss('release_search_page')+f'''
    {r} QLabel#download_heading {{font-size:{px(24)}px;font-weight:700;}}
    {r} QLabel#search_label {{font-size:{px(11)}px;font-weight:600;color:{c['muted']};}}
    {r} QLabel#search_tag {{color:{c['coral']};border:1px solid {c['line']};border-radius:5px;padding:4px 8px;font-size:{px(10)}px;}}
    {r} QFrame#search_panel {{background:{c['panel']};border:1px solid {c['line']};border-radius:14px;}}
    {r} QFrame#search_actions {{background:{c['bg']};border:none;border-top:1px solid {c['line']};}}
    {r} QLabel#search_status {{background:{c['raised']};color:{c['muted']};border:1px solid {c['line']};border-radius:8px;padding:10px 12px;font-size:{px(12)}px;}}
    {r} QComboBox, {r} QLineEdit {{background:{c['raised']};min-height:{px(42)}px;font-size:{px(14)}px;}}
    {r} QPushButton {{min-height:{px(40)}px;border-radius:9px;font-weight:600;font-size:{px(13)}px;}}
    {r} QLineEdit#search_url {{font-family:'JetBrains Mono';font-size:{px(11)}px;color:{c['muted']};min-height:{px(30)}px;}}
    {r} QTableView, {r} QListView {{background:{c['panel']};border:1px solid {c['line']};border-radius:12px;selection-background-color:{c['raised']};}}
    {r} QHeaderView::section {{background:{c['bg']};color:{c['muted']};border:none;border-bottom:1px solid {c['line']};padding:12px 8px;font-size:{px(10)}px;font-weight:600;}}
    {r} QProgressBar {{border:none;background:{c['raised']};}}
    {r} QProgressBar::chunk {{background:{c['coral']};}}
    {r} QCheckBox {{color:{c['text']};background:transparent;font-size:{px(13)}px;spacing:10px;min-height:{px(26)}px;}}
    {r} QScrollBar:horizontal {{height:8px;background:{c['bg']};}}
    {r} QScrollBar:vertical {{width:8px;background:{c['bg']};}}
    {r} QScrollBar::handle {{background:{c['line']};border-radius:4px;min-width:24px;min-height:24px;}}
    {r} QScrollBar::add-line, {r} QScrollBar::sub-line {{width:0;height:0;}}
    {r} QScrollBar::add-page, {r} QScrollBar::sub-page {{background:transparent;}}
    '''


def status_color(status,c):
    return c['ok'] if status=='In Library' else c['amber'] if status=='Match Uncertain' else c['coral'] if status=='Missing — Release Found' else c['muted']


class SearchCheckBox(QCheckBox):
    def paintEvent(self,event):
        c=colors();p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);rect=QRectF(1,(self.height()-px(19))/2,px(19),px(19))
        p.setPen(QPen(QColor(c['coral'] if self.isChecked() else c['muted']),1));p.setBrush(QColor(c['coral'] if self.isChecked() else c['bg']));p.drawRoundedRect(rect,5,5)
        if self.isChecked():
            p.setPen(QPen(QColor(c['on_coral']),2,Qt.SolidLine,Qt.RoundCap));x,y=rect.x(),rect.y();p.drawLine(int(x+px(4)),int(y+px(9)),int(x+px(8)),int(y+px(13)));p.drawLine(int(x+px(8)),int(y+px(13)),int(x+px(15)),int(y+px(5)))
        p.setPen(QColor(c['text']));p.setFont(self.font());p.drawText(self.rect().adjusted(px(29),0,-2,0),Qt.AlignVCenter|Qt.AlignLeft,self.text())
        if self.hasFocus():p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor(c['coral']),1));p.drawRoundedRect(QRectF(self.rect().adjusted(0,0,-1,-1)),5,5)


class ReleaseDelegate(QStyledItemDelegate):
    def editorEvent(self,event,model,option,index):
        if index.column()==0 and event.type() in (QEvent.MouseButtonPress,QEvent.MouseButtonRelease) and event.button()==Qt.LeftButton and event.pos().x()<option.rect.left()+px(45):
            if event.type()==QEvent.MouseButtonRelease:
                model.setData(index,Qt.Unchecked if index.data(Qt.CheckStateRole)==Qt.Checked else Qt.Checked,Qt.CheckStateRole)
            return True
        return super().editorEvent(event,model,option,index)
    def paint(self,painter,option,index):
        c=colors();painter.save();painter.setRenderHint(QPainter.Antialiasing);painter.setClipRect(option.rect)
        entry=index.model().rows[index.row()];checked=entry['identity'] in index.model().selected
        painter.fillRect(option.rect,QColor(c['panel'] if checked or option.state & (QStyle.State_Selected|QStyle.State_MouseOver) else c['bg']))
        painter.setPen(QColor(c['line']));painter.drawLine(option.rect.bottomLeft(),option.rect.bottomRight())
        rect=option.rect.adjusted(px(12),px(10),-px(12),-px(10));font=QFont('JetBrains Mono',10);font.setPixelSize(px(12));painter.setFont(font)
        if index.column()==0:
            indicator=QRectF(rect.left(),rect.center().y()-px(9),px(18),px(18));painter.setPen(QPen(QColor(c['coral'] if checked else c['line']),1.5));painter.setBrush(QColor(c['coral'] if checked else c['bg']));painter.drawRoundedRect(indicator,4,4)
            if checked:
                painter.setPen(QPen(QColor(c['on_coral']),2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));x,y=indicator.x(),indicator.y();painter.drawLine(int(x+4),int(y+9),int(x+8),int(y+13));painter.drawLine(int(x+8),int(y+13),int(x+14),int(y+5))
            rect.adjust(px(32),0,0,0);font.setBold(checked);painter.setFont(font)
        value=str(index.data() or '')
        color=status_color(entry.get('status'),c) if index.column()==6 else c['ok'] if index.column()==4 and (entry.get('seeders') or 0)>0 else c['text'] if index.column()==0 else c['muted']
        painter.setPen(QColor(color))
        if index.column()==6:
            font.setFamily('Plus Jakarta Sans');font.setPixelSize(px(11));painter.setFont(font);width=min(rect.width(),painter.fontMetrics().horizontalAdvance(value)+px(20));pill=QRectF(rect.left(),rect.center().y()-px(15),width,px(30));tint=QColor(color);tint.setAlpha(20);painter.setBrush(tint);painter.setPen(QPen(QColor(color),.7));painter.drawRoundedRect(pill,px(15),px(15));rect= pill.toRect().adjusted(px(10),0,-px(10),0)
        painter.drawText(rect,Qt.AlignVCenter|Qt.AlignLeft,painter.fontMetrics().elidedText(value,Qt.ElideRight,max(0,rect.width())))
        if option.state & QStyle.State_HasFocus:
            painter.setPen(QPen(QColor(c['coral']),2));painter.setBrush(Qt.NoBrush);painter.drawRect(option.rect.adjusted(1,1,-2,-2))
        painter.restore()


class AvailabilityDelegate(QStyledItemDelegate):
    def sizeHint(self,option,index):return QSize(px(270),px(82))
    def paint(self,painter,option,index):
        from app.core.download_discovery import episode_label
        entry=index.model().rows[index.row()];c=colors();color=status_color(entry['status'],c);painter.save();painter.setRenderHint(QPainter.Antialiasing)
        rect=option.rect.adjusted(5,5,-5,-5);painter.setPen(QPen(QColor(color if entry['status']=='In Library' else c['line']),1));painter.setBrush(QColor(c['bg']));painter.drawRoundedRect(QRectF(rect),10,10)
        rect.adjust(px(12),px(10),-px(12),-px(10));font=QFont('JetBrains Mono');font.setPixelSize(px(12));font.setBold(True);painter.setFont(font);painter.setPen(QColor(c['text']));painter.drawText(rect,Qt.AlignTop,episode_label(entry['episode']))
        font.setFamily('Plus Jakarta Sans');font.setBold(False);font.setPixelSize(px(11));painter.setFont(font);painter.setPen(QColor(color));painter.drawText(rect,Qt.AlignBottom,painter.fontMetrics().elidedText(entry['status'],Qt.ElideRight,rect.width()));painter.restore()
