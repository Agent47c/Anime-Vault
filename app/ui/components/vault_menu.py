"""Reference-style menus with real QActions and native keyboard navigation."""
from PyQt5.QtCore import Qt,QRectF,QPoint,QRect
from PyQt5.QtGui import QColor,QPainter,QPen,QFont
from PyQt5.QtWidgets import QLabel,QWidgetAction
from app.ui.components.dropdowns import ContainedMenu
from app.ui.home_style import colors,px
from app.ui.icons import icon


class VaultMenu(ContainedMenu):
    def __init__(self,parent=None,heading='VAULT NAVIGATOR',subtitle='',metadata='',width=360,context=False):
        super().__init__(parent)
        self.setProperty('animevaultRichMenu',True);self.setProperty('animevaultOwnScaledStyle',True)
        self.heading,self.subtitle,self.metadata=heading,subtitle,metadata
        self.menu_width=width;self.context=context;self._context_point=None
        self.setAccessibleName(heading);self.refresh_home_style()
        self._spacer(100 if context else 36,'header')

    def _spacer(self,height,kind):
        action=QWidgetAction(self);widget=QLabel();widget.setFixedHeight(px(height));widget.setAttribute(Qt.WA_TransparentForMouseEvents);widget.setFocusPolicy(Qt.NoFocus)
        action.setDefaultWidget(widget);action.setEnabled(False);action.setProperty('richKind',kind);self.addAction(action)
        return action

    def add_item(self,text,callback,graphic=None,hint='',description='',danger=False):
        action=self.addAction(text,callback)
        action.setProperty('richIcon',graphic);action.setProperty('richHint',hint);action.setProperty('richDescription',description);action.setProperty('richDanger',danger)
        if description:action.setToolTip(text+' · '+description)
        return action

    def add_footer(self,text='Anime Vault · Library tools'):
        self.footer=text;self._spacer(30,'footer')

    def refresh_home_style(self):
        c=colors();self.setMinimumWidth(px(self.menu_width))
        self.setStyleSheet(f"QMenu {{background:{c['panel']};border:1px solid {c['line']};border-radius:16px;padding:10px;font-size:{px(14)}px;menu-scrollable:1;}} "
                           f"QMenu::item {{min-height:{px(30)}px;padding:8px 18px;}} QMenu::separator {{height:1px;margin:6px 10px;background:{c['line']};}}")

    def _prepare_bounds(self):
        self.refresh_home_style();super()._prepare_bounds()

    def exec_(self,point,*args):
        if self.context:self._context_point=point
        return super().exec_(point,*args)

    def _fit(self):
        if not self.context or self._context_point is None:return super()._fit()
        if not self.isVisible():return
        bounds=self._bounds();size=self.size().boundedTo(bounds.size());point=self._context_point
        self.setGeometry(QRect(QPoint(max(bounds.left(),min(point.x(),bounds.right()-size.width()+1)),max(bounds.top(),min(point.y(),bounds.bottom()-size.height()+1))),size))

    def paintEvent(self,event):
        c=colors();p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(QPen(QColor(c['line']),1));p.setBrush(QColor(c['panel']));p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),16,16)
        for action in self.actions():
            if not action.isVisible():continue
            rect=self.actionGeometry(action).adjusted(2,1,-2,-1)
            if action.isSeparator():
                p.setPen(QPen(QColor(c['line']),1));p.drawLine(rect.left()+8,rect.center().y(),rect.right()-8,rect.center().y());continue
            kind=action.property('richKind')
            font=QFont('Plus Jakarta Sans');font.setPixelSize(px(14));p.setFont(font)
            if kind:
                p.setPen(QColor(c['muted']));font.setPixelSize(px(11));font.setBold(kind=='header');p.setFont(font)
                if kind=='footer':p.drawText(rect.adjusted(10,0,-10,0),Qt.AlignVCenter,getattr(self,'footer',''));continue
                if not self.context:
                    p.setPen(Qt.NoPen);p.setBrush(QColor(c['coral']));p.drawEllipse(QPoint(rect.left()+12,rect.center().y()),3,3)
                    p.setPen(QColor(c['muted']));p.drawText(rect.adjusted(24,0,-10,0),Qt.AlignVCenter,self.heading)
                else:
                    p.setPen(QColor(c['coral']));p.drawText(rect.adjusted(10,0,-10,-px(56)),Qt.AlignTop|Qt.TextWordWrap,self.heading)
                if self.context:
                    font.setPixelSize(px(14));p.setFont(font);p.setPen(QColor(c['text']));p.drawText(rect.adjusted(10,px(42),-10,-px(25)),Qt.AlignVCenter,p.fontMetrics().elidedText(self.subtitle,Qt.ElideRight,rect.width()-20))
                    font.setPixelSize(px(11));p.setFont(font);p.setPen(QColor(c['amber']));p.drawText(rect.adjusted(10,px(68),-10,0),Qt.AlignTop,self.metadata)
                continue
            selected=action is self.activeAction() or bool(action.property('richActive'))
            if selected:
                tint=QColor(c['coral']);tint.setAlpha(45);p.setPen(Qt.NoPen);p.setBrush(tint);p.drawRoundedRect(QRectF(rect),9,9)
                p.setBrush(QColor(c['coral']));p.drawRoundedRect(QRectF(rect.left(),rect.top()+6,3,rect.height()-12),1.5,1.5)
            color=c['coral'] if action.property('richDanger') else c['text'] if action.isEnabled() else c['muted']
            graphic=action.property('richIcon');left=rect.left()+12
            if graphic:icon(graphic,c['coral'] if selected else color).paint(p,left,rect.center().y()-10,20,20)
            left+=32
            hint=action.property('richHint') or '';right=rect.right()-12
            if hint:
                small=QFont('JetBrains Mono');small.setPixelSize(px(11));p.setFont(small);width=p.fontMetrics().horizontalAdvance(hint)+14
                badge=QRectF(right-width,rect.center().y()-11,width,22);p.setBrush(QColor(c['raised']));p.setPen(Qt.NoPen);p.drawRoundedRect(badge,5,5);p.setPen(QColor(c['muted']));p.drawText(badge,Qt.AlignCenter,hint);right-=width+10
            font.setPixelSize(px(14));font.setBold(selected);p.setFont(font);p.setPen(QColor(color))
            area=rect.adjusted(left-rect.left(),0,right-rect.right(),0)
            description=action.property('richDescription')
            if description:
                p.drawText(area.adjusted(0,2,0,-px(19)),Qt.AlignVCenter,action.text())
                font.setPixelSize(px(11));p.setFont(font);p.setPen(QColor(c['muted']));p.drawText(area.adjusted(0,px(22),0,0),Qt.AlignVCenter,p.fontMetrics().elidedText(description,Qt.ElideRight,area.width()))
            else:p.drawText(area,Qt.AlignVCenter|Qt.TextWordWrap,action.text())
