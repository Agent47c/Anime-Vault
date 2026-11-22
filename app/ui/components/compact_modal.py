"""Compact Manga dialogs over a once-blurred, bounded background snapshot."""
from PyQt5 import sip
from PyQt5.QtCore import Qt,QObject,QEvent,QTimer,QRectF,QRect,QPoint
from PyQt5.QtGui import QImage,QPixmap,QPainter,QColor,QFont,QPen
from PyQt5.QtWidgets import QWidget,QFrame,QVBoxLayout,QApplication
from app.ui.home_style import px
from app.ui.manga_style import manga_colors,material
from app.ui.theme_catalog import is_manga_dark

SHADOW=18


def blur_snapshot(pixmap):
    """Blur once at bounded resolution; never attach an effect to live pages."""
    from PIL import Image,ImageFilter
    image=pixmap.toImage()
    if image.width()>1280 or image.height()>800:image=image.scaled(1280,800,Qt.KeepAspectRatio,Qt.FastTransformation)
    image=image.convertToFormat(QImage.Format_RGBA8888)
    if image.isNull():return QPixmap()
    bits=image.bits();bits.setsize(image.byteCount())
    source=Image.frombytes('RGBA',(image.width(),image.height()),bytes(bits),'raw','RGBA',image.bytesPerLine())
    blurred=source.filter(ImageFilter.GaussianBlur(4))
    raw=blurred.tobytes()
    return QPixmap.fromImage(QImage(raw,blurred.width,blurred.height,blurred.width*4,QImage.Format_RGBA8888).copy())


class BlurredBackdrop(QWidget):
    def __init__(self,source,parent=None):
        super().__init__(parent);self.image=blur_snapshot(source)
        self.setObjectName('compact_modal_backdrop')
        self.setAttribute(Qt.WA_TransparentForMouseEvents,True)
        self.setAttribute(Qt.WA_ShowWithoutActivating,True)
        self.setFocusPolicy(Qt.NoFocus)
    def paint_background(self,painter,target):
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(target,QColor(manga_colors()['bg']))
        painter.drawPixmap(target,self.image)
        tint=QColor(0,0,0,120) if is_manga_dark() else QColor(91,102,126,85)
        painter.fillRect(target,tint)
    def paintEvent(self,event):
        painter=QPainter(self)
        self.paint_background(painter,self.rect())
        painter.end()


class ModalSurface(QFrame):
    def __init__(self,glyph):
        super().__init__();self.glyph=glyph;self.setObjectName('compact_modal_surface')
    def paintEvent(self,event):
        from app.ui.components.neumorphic import paint_depth
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        face=QRectF(self.rect()).adjusted(SHADOW,SHADOW,-SHADOW,-SHADOW)
        paint_depth(p,face,radius=22)
        colors=manga_colors()
        p.setBrush(QColor(colors['panel']));p.setPen(QPen(QColor(colors['line'] if is_manga_dark() else '#d9dee8'),1));p.drawRoundedRect(face,22,22)
        if self.glyph and QApplication.instance().property('animevaultDecorations') is not False:
            p.setPen(QColor(166,175,195,28));p.setFont(QFont('Yu Gothic',54,QFont.Bold))
            p.drawText(face.adjusted(20,8,-20,-8),Qt.AlignTop|Qt.AlignRight,self.glyph)
        p.end()


def modal_qss(name):
    r=f'QWidget#{name}'
    return material(f'''
    {r} {{background:transparent;border:none;}}
    {r} QWidget#compact_modal_content, {r} QFrame#compact_modal_surface,
    {r} QWidget#workflow_header, {r} QWidget#workflow_body,
    {r} QFrame#workflow_footer, {r} QScrollArea, {r} QScrollArea>QWidget {{background:transparent;border:none;}}
    {r} QLabel#dialog_title, {r} QLabel#workflow_title {{font:800 {px(25)}px 'Noto Serif';}}
    {r} QLabel#dialog_subtitle {{font-size:{px(12)}px;}}
    {r} QWidget#adult_header {{background:transparent;border:none;}}
    {r} QLineEdit {{min-height:{px(44)}px;border-radius:12px;padding:0 12px;}}
    {r} QPushButton {{min-height:{px(38)}px;}}
    {r} QFrame#quit_status {{background:#f1f3f7;border:1px solid #dce1eb;border-radius:14px;}}
    {r} QFrame#quit_choice[selected='true'] {{background:white;border:2px solid #ff2e93;}}
    {r} QLabel#workflow_match[tone='success'] {{background:#e8f8f0;color:#087b60;border:1px solid #c6ecd6;border-radius:10px;padding:4px 10px;}}
    {r} QLabel#group_notice {{background:#eef0f5;border:1px solid #e2e5ed;border-radius:10px;padding:12px;font-size:{px(12)}px;}}
    {r} QCheckBox#group_reviewed {{background:#f1f3f7;border:1px solid #e2e5ed;border-radius:10px;padding:8px;}}
    {r} QLabel#group_badge[primary='true'] {{background:#ff2e93;color:#111217;border:none;}}
    ''')


def install(dialog,width,glyph=''):
    if hasattr(dialog,'_compact_modal'):return
    old=dialog.layout();content=QWidget();content.setObjectName('compact_modal_content');content.setLayout(old)
    surface=ModalSurface(glyph);inside=QVBoxLayout(surface);inside.setContentsMargins(SHADOW,SHADOW,SHADOW,SHADOW);inside.addWidget(content)
    root=QVBoxLayout(dialog);root.setContentsMargins(0,0,0,0);root.addWidget(surface)
    dialog.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
    # Avoid native layered-window alpha hit testing around child/effect regions.
    # Paint an opaque crop of the blurred backing instead; the rounded surface
    # and its surrounding shadow keep the same appearance.
    dialog.setAttribute(Qt.WA_TranslucentBackground,False)
    dialog.setAttribute(Qt.WA_OpaquePaintEvent,True)
    dialog.setProperty('animevaultThemeScope',True);dialog.setProperty('animevaultOwnScaledStyle',True)
    dialog.compact_manga_modal=True
    controller=ModalController(dialog,content,width)
    controller.capture_background()
    dialog._compact_modal=controller
    dialog.installEventFilter(controller)
    dialog.finished.connect(controller.clear)
    dialog.destroyed.connect(controller.clear)


class ModalController(QObject):
    def __init__(self,dialog,content,width):
        super().__init__(dialog);self.dialog=dialog;self.content=content;self.width=width
        self.backdrop=None;self.host=None;self._fitting=False
        self.backplate=QPixmap()
        self.background=QPixmap()
    def capture_background(self):
        # A visible owned dialog can be included in QWidget.grab() on Windows.
        # Capture while hidden so its old position/footer cannot enter the blur.
        parent=self.dialog.parentWidget()
        if parent and not self.dialog.isVisible():
            snapshot=parent.window().grab()
            if snapshot.width()>1280 or snapshot.height()>800:
                snapshot=snapshot.scaled(1280,800,Qt.KeepAspectRatio,Qt.FastTransformation)
            self.background=snapshot
    def cache_backplate(self):
        if sip.isdeleted(self.dialog):return
        self.backplate=QPixmap(self.dialog.size());self.backplate.fill(QColor(manga_colors()['bg']))
        if self.host is not None and self.backdrop is not None:
            origin=self.backdrop.mapFromGlobal(self.dialog.mapToGlobal(QPoint()))
            target=QRect(-origin,self.backdrop.size())
            painter=QPainter(self.backplate)
            self.backdrop.paint_background(painter,target)
            painter.end()
        self.dialog.update()
    def ensure_front(self):
        if sip.isdeleted(self.dialog) or not self.dialog.isVisible():return
        modal=QApplication.activeModalWidget()
        if modal is None or modal is self.dialog:
            self.dialog.raise_();self.dialog.activateWindow()
    def fit(self):
        if self._fitting or sip.isdeleted(self.dialog):return
        self._fitting=True
        try:
            d=self.dialog;face=px(self.width);d.setFixedWidth(face+2*SHADOW);self.content.setFixedWidth(face)
            d.ensurePolished();layout=self.content.layout();layout.activate()
            header=self.content.findChild(QWidget,'workflow_header')
            body=self.content.findChild(QWidget,'workflow_body')
            footer=self.content.findChild(QWidget,'workflow_footer')
            def height(widget):
                box=widget.layout()
                return max(box.minimumSize().height(),box.heightForWidth(face) if box.hasHeightForWidth() else box.sizeHint().height())
            if header and body and footer:
                wanted=height(header)+height(body)+height(footer)+2*SHADOW
            else:
                wanted=max(layout.sizeHint().height(),layout.heightForWidth(face) if layout.hasHeightForWidth() else 0)+2*SHADOW
            parent=d.parentWidget();host=parent.window() if parent else None
            available=(host.height() if host and host.height()>300 else d.screen().availableGeometry().height())-32
            d.resize(d.width(),min(max(px(220),wanted),available))
            if host:
                d.move(host.mapToGlobal(host.rect().center())-d.rect().center())
            if d.isVisible():self.cache_backplate()
        finally:self._fitting=False
    def clear(self,*_):
        if self.host is not None and not sip.isdeleted(self.host):self.host.removeEventFilter(self)
        self.host=None
        if self.backdrop is not None and not sip.isdeleted(self.backdrop):self.backdrop.hide();self.backdrop.deleteLater()
        self.backdrop=None
        self.backplate=QPixmap()
    def eventFilter(self,obj,event):
        if obj is self.dialog:
            if event.type()==QEvent.Show:
                self.fit()
                focus=getattr(self.dialog,'_modal_initial_focus',None)
                if focus is not None:
                    QTimer.singleShot(0,lambda:focus.setFocus(Qt.OtherFocusReason) if not sip.isdeleted(focus) else None)
                parent=self.dialog.parentWidget()
                if parent and self.backdrop is None:
                    self.host=parent.window()
                    self.backdrop=BlurredBackdrop(self.background,self.host)
                    self.backdrop.setGeometry(self.host.rect());self.backdrop.show();self.backdrop.raise_()
                    self.host.installEventFilter(self)
                self.cache_backplate()
                QTimer.singleShot(0,self.ensure_front)
            elif event.type()==QEvent.Hide:self.clear()
            elif event.type()==QEvent.Polish and not self.dialog.isVisible():self.capture_background()
            elif event.type() in (QEvent.Resize,QEvent.Move) and self.dialog.isVisible():self.cache_backplate()
            elif event.type()==QEvent.LayoutRequest and self.dialog.isVisible():QTimer.singleShot(0,self.fit)
            elif event.type()==QEvent.Paint:
                p=QPainter(self.dialog)
                p.fillRect(self.dialog.rect(),QColor(manga_colors()['bg']))
                if not self.backplate.isNull():p.drawPixmap(0,0,self.backplate)
                p.end();return True
        elif obj is self.host and event.type()==QEvent.Resize:
            if self.backdrop:self.backdrop.setGeometry(self.host.rect())
            self.fit()
        return False
