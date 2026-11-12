"""Keep combo popups consistent across Windows and Qt styles."""
from PyQt5.QtCore import QObject, QEvent,Qt,QSize,QRectF,QRect,QPoint,QTimer
from PyQt5.QtGui import QPainter,QColor,QPen,QFont,QFontMetrics
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate,QMenu,QStyle,QApplication,QAbstractItemView


def dropdown_font():
    from app.ui.home_style import px
    font=QFont('Plus Jakarta Sans');font.setPixelSize(px(14));return font


def menu_colors():
    from app.ui.home_style import colors
    return colors()


class ContainedMenu(QMenu):
    """Keep a header menu inside its owning window."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.aboutToShow.connect(self._prepare_bounds)

    def _bounds(self):
        owner=self.parentWidget().window()
        return QRect(owner.mapToGlobal(QPoint()),owner.size()).intersected(owner.screen().availableGeometry()).adjusted(8,8,-8,-8)

    def _prepare_bounds(self):
        bounds=self._bounds()
        # QMenu scrolls against screen bounds, not its owner's bounds. Reduce
        # excess row padding first so resizing never clips the final action.
        styler=getattr(QApplication.instance(),'_dropdown_styler',None)
        if styler:
            self.setProperty('unifiedMenuSignature',None);styler.style_popup(self)
            self.ensurePolished()
            if self.sizeHint().height()>bounds.height():
                actions=[action for action in self.actions() if action.isVisible() and not action.isSeparator()]
                separators=sum(action.isSeparator() for action in self.actions() if action.isVisible())
                row_height=max(QFontMetrics(dropdown_font()).height(),(bounds.height()-20-separators*13)//max(1,len(actions)))
                padding=max(0,(row_height-QFontMetrics(dropdown_font()).height())//2)
                self.setStyleSheet(self.styleSheet()+f'\nQMenu::item {{min-height:0px;padding:{padding}px 28px {padding}px 16px;}}')
        self.setMaximumSize(max(1,bounds.width()),max(1,bounds.height()))

    def showEvent(self,event):
        super().showEvent(event)
        self._fit()
        QTimer.singleShot(0,self._fit)

    def _fit(self):
        from PyQt5 import sip
        if sip.isdeleted(self) or not self.isVisible():return
        bounds=self._bounds();size=self.size().boundedTo(bounds.size())
        anchor=self.parentWidget().mapToGlobal(QPoint(self.parentWidget().width(),self.parentWidget().height()+4))
        x=max(bounds.left(),min(anchor.x()-size.width(),bounds.right()-size.width()+1))
        y=max(bounds.top(),min(anchor.y(),bounds.bottom()-size.height()+1))
        self.setGeometry(QRect(QPoint(x,y),size))


class DropdownDelegate(QStyledItemDelegate):
    """One painted row, retaining the combo's model, keyboard and search behavior."""
    def paint(self,painter,option,index):
        from app.ui.home_style import px
        c=menu_colors();painter.save();painter.setRenderHint(QPainter.Antialiasing)
        rect=option.rect.adjusted(4,2,-4,-2);enabled=bool(index.flags()&Qt.ItemIsEnabled)
        hovered=bool(option.state&(QStyle.State_Selected|QStyle.State_MouseOver))
        current=index.row()==self.parent().currentIndex()
        if hovered and enabled:
            fill=QColor(c['raised'] if QApplication.instance().property('animevaultHighContrast') else c['coral'])
            if not QApplication.instance().property('animevaultHighContrast'):fill.setAlpha(32)
            painter.setPen(Qt.NoPen);painter.setBrush(fill);painter.drawRoundedRect(QRectF(rect),8,8)
            painter.setBrush(QColor(c['coral']));painter.drawRoundedRect(QRectF(rect.left(),rect.top()+8,3,rect.height()-16),1.5,1.5)
        painter.setFont(dropdown_font())
        painter.setPen(QColor(c['text'] if enabled else c['muted']))
        text=rect.adjusted(px(14),0,-px(34),0);graphic=index.data(Qt.DecorationRole)
        if graphic:
            graphic.paint(painter,text.left(),text.center().y()-9,18,18);text.adjust(26,0,0,0)
        painter.drawText(text,Qt.AlignVCenter|Qt.AlignLeft|Qt.TextWordWrap|Qt.TextWrapAnywhere,str(index.data() or ''))
        if current:
            painter.setPen(QPen(QColor(c['coral']),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            x=rect.right()-px(21);y=rect.center().y();painter.drawLine(x-4,y,x-1,y+3);painter.drawLine(x-1,y+3,x+5,y-4)
        painter.restore()
    def sizeHint(self,option,index):
        from app.ui.home_style import px
        metrics=QFontMetrics(dropdown_font());value=str(index.data() or '')
        extra=px(26) if index.data(Qt.DecorationRole) else 0
        width=getattr(self.parent(),'_dropdown_row_width',0)
        natural=metrics.horizontalAdvance(value)+px(64)+extra
        if not width:return QSize(natural,px(44))
        wrapped=metrics.boundingRect(QRect(0,0,max(1,width-px(56)-extra),100000),Qt.TextWordWrap|Qt.TextWrapAnywhere,value)
        return QSize(natural,max(px(44),wrapped.height()+px(20)))


class DropdownStyler(QObject):
    def style_combo(self, combo):
        if combo.property("animevaultStyledDropdown"):
            return
        # Qt's native menu delegate bypasses popup item QSS on Windows.
        combo.setItemDelegate(DropdownDelegate(combo))
        combo.view().setMouseTracking(True)
        combo.view().setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        combo.view().setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        if hasattr(combo.view(),'setUniformItemSizes'):combo.view().setUniformItemSizes(False)
        if hasattr(combo.view(),'setWordWrap'):combo.view().setWordWrap(True)
        combo.setProperty("animevaultStyledDropdown", True)

    def fit_popup(self,popup,available=None):
        """Measure the font actually painted, reserving check/icon/scroll space."""
        from PyQt5 import sip
        from PyQt5.QtWidgets import QStyleOptionViewItem
        from app.ui.home_style import px
        if sip.isdeleted(popup) or not popup.isVisible():return
        combo=popup.parentWidget()
        while combo is not None and not isinstance(combo,QComboBox):combo=combo.parentWidget()
        if combo is None or sip.isdeleted(combo):return
        view=combo.view();model=combo.model();column=combo.modelColumn();root=combo.rootModelIndex()
        metrics=QFontMetrics(dropdown_font());natural=0
        for row in range(model.rowCount(root)):
            index=model.index(row,column,root)
            natural=max(natural,metrics.horizontalAdvance(str(index.data() or ''))+(px(26) if index.data(Qt.DecorationRole) else 0))
        screen=available or combo.screen().availableGeometry()
        chrome_x=max(px(24),popup.width()-view.viewport().width())
        chrome_y=max(px(28),popup.height()-view.viewport().height())
        width=min(max(combo.width(),natural+px(64)+chrome_x),screen.width()-16)
        combo._dropdown_row_width=max(1,width-chrome_x)
        option=QStyleOptionViewItem();option.rect=QRect(0,0,combo._dropdown_row_width,1)
        heights=[combo.itemDelegate().sizeHint(option,model.index(row,column,root)).height() for row in range(model.rowCount(root))]
        height=min(sum(heights)+chrome_y,px(44)*min(12,max(1,combo.maxVisibleItems()))+chrome_y,screen.height()-16)
        point=combo.mapToGlobal(QPoint(0,combo.height()+4));top=combo.mapToGlobal(QPoint()).y()
        x=max(screen.left()+8,min(point.x(),screen.right()-width-7))
        y=point.y()
        if y+height>screen.bottom()-8 and top-screen.top()>screen.bottom()-point.y():y=top-height-4
        y=max(screen.top()+8,min(y,screen.bottom()-height-7))
        popup.setMinimumSize(0,0);popup.setMaximumSize(16777215,16777215)
        popup.setGeometry(x,y,width,max(px(44),height))
        if popup.layout():popup.layout().activate()
        view.doItemsLayout();view.scrollTo(model.index(combo.currentIndex(),column,root),QAbstractItemView.EnsureVisible)

    def style_popup(self,obj):
        if isinstance(obj,QMenu) and obj.property('animevaultRichMenu'):return
        from app.ui.home_style import px
        c=menu_colors();signature=(tuple(c.items()),px(14))
        if obj.property('unifiedMenuSignature')==signature:return
        obj.setProperty('unifiedMenuSignature',signature)
        obj.setProperty('animevaultOwnScaledStyle',True)
        if isinstance(obj,QMenu):
            tint=QColor(c['coral']);tint.setAlpha(32)
            hover=c['raised'] if QApplication.instance().property('animevaultHighContrast') else f'rgba({tint.red()},{tint.green()},{tint.blue()},32)'
            obj.setStyleSheet(f'''QMenu {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:12px;padding:8px;font-family:'Plus Jakarta Sans';font-size:{px(14)}px;menu-scrollable:1;}}
                QMenu::item {{padding:10px 28px 10px 16px;min-height:{px(22)}px;border-radius:8px;color:{c['text']};}}
                QMenu::item:selected {{background:{hover};color:{c['text']};border-left:3px solid {c['coral']};}}
                QMenu::item:disabled {{color:{c['muted']};}}
                QMenu::separator {{height:1px;background:{c['line']};margin:6px 8px;}}
                QMenu::section {{color:{c['muted']};padding:8px 14px;font-family:'JetBrains Mono';font-size:{px(11)}px;}}''')
        else:
            obj.setObjectName('unified_dropdown_popup')
            obj.setStyleSheet(f'''QWidget#unified_dropdown_popup {{background:{c['panel']};border:1px solid {c['line']};border-radius:12px;padding:6px;}}
                QAbstractItemView {{background:{c['panel']};color:{c['text']};border:none;outline:none;padding:4px;}}
                QAbstractItemView::item {{padding:0;border:none;}}''')

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Polish and isinstance(obj, QComboBox):
            self.style_combo(obj)
        if event.type()==QEvent.Show:
            if isinstance(obj,QMenu):self.style_popup(obj)
            elif isinstance(obj,QComboBox):self.style_combo(obj)
            elif obj.metaObject().className()=='QComboBoxPrivateContainer':
                self.style_popup(obj)
                QTimer.singleShot(0,lambda popup=obj:self.fit_popup(popup))
        return False


def install_dropdown_style(app):
    if not hasattr(app, "_dropdown_styler"):
        app._dropdown_styler = DropdownStyler(app)
        app.installEventFilter(app._dropdown_styler)
    for widget in app.allWidgets():
        if isinstance(widget, QComboBox):
            app._dropdown_styler.style_combo(widget)
