"""Shared dropdown shadows without capturing combo popup windows as effects."""
from PyQt5.QtCore import QEvent, Qt, QRectF
from PyQt5.QtWidgets import QWidget
from app.ui.components.neumorphic import PAD, paint_depth


def option_face(painter,rect,selected=False,enabled=True):
    """The same small raised button material for every popup option."""
    from PyQt5.QtGui import QColor,QPen
    painter.save()
    if not enabled:painter.setOpacity(.55)
    rect=QRectF(rect)
    if not selected:
        painter.save();painter.setOpacity(painter.opacity()*.65);paint_depth(painter,rect,radius=8);painter.restore()
    painter.setPen(QPen(QColor('#ff2e93') if selected else QColor(17,18,23,75),.75))
    painter.setBrush(QColor('#eef0f5' if selected else 'white'));painter.drawRoundedRect(rect,8,8)
    if selected:paint_depth(painter,rect,True,radius=8)
    painter.restore()


class ComboDepth(QWidget):
    """A reusable, input-transparent sibling keeps native combo painting intact."""
    def __init__(self,combo):
        super().__init__(combo.parentWidget())
        self.combo=combo
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet('background:transparent;border:none;')
        combo.installEventFilter(self)
        combo.destroyed.connect(self.deleteLater)
        self.sync()

    def sync(self):
        from app.ui.manga_pages import active
        from PyQt5.QtWidgets import QApplication
        combo=self.combo
        enabled=active() and not QApplication.instance().property('animevaultHighContrast')
        if self.parentWidget() is not combo.parentWidget():self.setParent(combo.parentWidget())
        if not enabled or not combo.isVisible() or combo.parentWidget() is None:
            self.hide();return
        self.setGeometry(combo.geometry().adjusted(-PAD,-PAD,PAD,PAD))
        self.stackUnder(combo);self.show();self.update()

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Show,QEvent.Hide,QEvent.Move,QEvent.Resize,QEvent.ParentChange,QEvent.EnabledChange):self.sync()
        return False

    def paintEvent(self,event):
        from PyQt5.QtGui import QPainter
        painter=QPainter(self)
        if not self.combo.isEnabled():painter.setOpacity(.45)
        paint_depth(painter,QRectF(self.rect()).adjusted(PAD,PAD,-PAD,-PAD),radius=8)


class PopupDepth(QWidget):
    def __init__(self,popup):
        super().__init__(popup)
        from PyQt5.QtWidgets import QMenu
        self.paint_face=not isinstance(popup,QMenu)
        self.menu=popup if isinstance(popup,QMenu) else None
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet('background:transparent;border:none;')
        popup.installEventFilter(self)
        if self.menu:self.menu.hovered.connect(lambda *_:self.update())

    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Resize,QEvent.Show):
            self.setGeometry(obj.rect())
            if self.paint_face:self.lower()
            else:self.raise_()
        elif event.type() in (QEvent.Leave,QEvent.ActionChanged,QEvent.ActionAdded,QEvent.ActionRemoved):self.update()
        return False

    def paintEvent(self,event):
        from PyQt5.QtGui import QPainter,QColor,QPen
        painter=QPainter(self)
        face=QRectF(self.rect()).adjusted(PAD,PAD,-PAD,-PAD)
        paint_depth(painter,face,radius=12)
        if self.paint_face:
            from app.ui.home_style import colors
            c=colors();painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(c['line']),1));painter.setBrush(QColor(c['panel']));painter.drawRoundedRect(face,12,12)
        elif self.menu:
            self.paint_options(painter,face)

    def paint_options(self,painter,face):
        from PyQt5.QtGui import QColor,QFontMetrics
        from app.ui.components.dropdowns import dropdown_font
        from app.ui.home_style import colors
        from app.ui.icons import icon
        c=colors();painter.save();painter.setRenderHint(painter.Antialiasing);painter.setClipRect(face.adjusted(4,4,-4,-4))
        for action in self.menu.actions():
            if not action.isVisible() or action.isSeparator():continue
            from PyQt5.QtWidgets import QWidgetAction
            if isinstance(action,QWidgetAction):continue
            native=self.menu.actionGeometry(action)
            gap=min(5,max(1,(native.height()-QFontMetrics(dropdown_font()).height()-4)//2))
            rect=QRectF(native.adjusted(4,gap,-4,-gap))
            if rect.height()<4 or not rect.intersects(face):continue
            selected=action is self.menu.activeAction()
            option_face(painter,rect,selected,action.isEnabled())
            font=dropdown_font();font.setBold(action is self.menu.defaultAction());painter.setFont(font)
            left=rect.left()+12;right=rect.right()-12
            graphic=action.icon()
            if not graphic.isNull():
                graphic.paint(painter,int(left),int(rect.center().y()-9),18,18);left+=26
            elif action.isCheckable():
                if action.isChecked():icon('check',c['coral']).paint(painter,int(left),int(rect.center().y()-8),16,16)
                left+=24
            if action.menu():
                icon('chevron-right',c['muted']).paint(painter,int(right-12),int(rect.center().y()-7),14,14);right-=22
            label,_,embedded=action.text().partition('\t')
            shortcut=embedded or action.shortcut().toString()
            if shortcut:
                metrics=QFontMetrics(font);width=metrics.horizontalAdvance(shortcut)
                painter.setPen(QColor(c['muted']));painter.drawText(QRectF(right-width,rect.top(),width,rect.height()),Qt.AlignVCenter|Qt.AlignRight,shortcut);right-=width+20
            painter.setPen(QColor(c['text'] if action.isEnabled() else c['muted']))
            painter.drawText(QRectF(left,rect.top(),max(1,right-left),rect.height()),Qt.AlignVCenter|Qt.AlignLeft|Qt.TextHideMnemonic,label)
        painter.restore()


def combo_depth(combo,enabled):
    shade=getattr(combo,'_manga_combo_depth',None)
    if enabled and shade is None:
        shade=ComboDepth(combo);combo._manga_combo_depth=shade
    if shade:
        if enabled:shade.sync()
        else:shade.hide()


def popup_depth(popup,enabled,rich=False):
    from PyQt5.QtWidgets import QApplication
    from PyQt5 import sip
    app=QApplication.instance()
    if not hasattr(app,'_dropdown_depth_surfaces'):app._dropdown_depth_surfaces={}
    registry=app._dropdown_depth_surfaces;key=int(sip.unwrapinstance(popup))
    if not popup.property('mangaDepthHasBase'):
        popup.setProperty('mangaDepthHasBase',True)
        popup.setProperty('mangaDepthTranslucentBase',popup.testAttribute(Qt.WA_TranslucentBackground))
        popup.setProperty('mangaDepthWindowFlags',int(popup.windowFlags()))
    base_flags=Qt.WindowFlags(popup.property('mangaDepthWindowFlags'))
    flags=base_flags|Qt.FramelessWindowHint|Qt.NoDropShadowWindowHint if enabled else base_flags
    # Windows requires a frameless window for per-pixel transparency. Set it
    # before showing, and disable the native shadow so it cannot form a black box.
    if not popup.isVisible() and popup.windowFlags()!=flags:popup.setWindowFlags(flags)
    popup.setAttribute(Qt.WA_TranslucentBackground,True if enabled else bool(popup.property('mangaDepthTranslucentBase')))
    # Native combo containers get temporary Python wrappers. Keep the Python
    # paint implementation alive until the actual Qt popup is destroyed.
    shade=registry.get(key)
    if enabled and not rich and shade is None:
        shade=PopupDepth(popup);registry[key]=shade
        popup.destroyed.connect(lambda *_:registry.pop(key,None))
    if shade:
        shade.setVisible(enabled and not rich)
        if enabled:
            shade.setGeometry(popup.rect())
            if shade.paint_face:shade.lower()
            else:shade.raise_()
