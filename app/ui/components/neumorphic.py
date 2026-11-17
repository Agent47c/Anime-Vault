"""Cached nine-slice dual shadows and inset wells for the Manga master controls.

Only tiny 192px masks are blurred once. Painting reuses them; no file IO,
per-frame Gaussian blur, extra widgets, or whole-page effects are introduced.
"""
from PyQt5.QtCore import QRectF,QPoint,Qt
from PyQt5.QtGui import QImage,QPixmap,QPainter,QColor
from PyQt5.QtWidgets import QGraphicsEffect,QAbstractButton,QApplication,QWidget,QFrame,QComboBox

_tiles={}
PAD=12


def tile(inset=False,radius=12):
    key=(inset,radius)
    if key in _tiles:return _tiles[key]
    from PIL import Image,ImageDraw,ImageFilter,ImageChops
    size=192;mask=Image.new('L',(size,size));ImageDraw.Draw(mask).rounded_rectangle((24,24,168,168),radius=radius*2,fill=255)
    def shifted(source,x,y):
        result=Image.new('L',(size,size));result.paste(source,(x,y));return result
    image=Image.new('RGBA',(size,size))
    layers=(((0,8),(255,46,147),150),) if inset=='glow' else (((3,3),(103,113,137),100),((-2,-2),(255,255,255),55)) if inset else (((-5,-5),(255,255,255),170),((7,7),(103,113,137),125))
    for offset,color,alpha in layers:
        if inset is True:
            source=shifted(ImageChops.invert(mask),*offset).filter(ImageFilter.GaussianBlur(5))
            source=ImageChops.multiply(source,mask)
        else:
            source=shifted(mask,*offset).filter(ImageFilter.GaussianBlur(7))
            source=ImageChops.multiply(source,ImageChops.invert(mask))
        layer=Image.new('RGBA',(size,size),color+(0,));layer.putalpha(source.point(lambda value:int(value*alpha/255)));image=Image.alpha_composite(image,layer)
    data=image.tobytes();qimage=QImage(data,size,size,size*4,QImage.Format_RGBA8888).copy()
    _tiles[key]=QPixmap.fromImage(qimage);return _tiles[key]


def paint_depth(painter,rect,inset=False,radius=12):
    source=tile(inset,radius);face=QRectF(rect);rect=face.adjusted(-PAD,-PAD,PAD,PAD)
    # 24px shadow padding + 24px corners at 2x; center stretches freely.
    edge=min(24,rect.height()/2,rect.width()/2)
    xs=[rect.left(),rect.left()+edge,rect.right()-edge,rect.right()]
    ys=[rect.top(),rect.top()+edge,rect.bottom()-edge,rect.bottom()]
    ss=[0,48,144,192]
    painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform)
    if inset is True:
        from PyQt5.QtGui import QPainterPath
        clip=QPainterPath();clip.addRoundedRect(face.adjusted(1,1,-1,-1),max(0,radius-1),max(0,radius-1));painter.setClipPath(clip,Qt.IntersectClip)
    for y in range(3):
        for x in range(3):
            if xs[x+1]>xs[x] and ys[y+1]>ys[y]:painter.drawPixmap(QRectF(xs[x],ys[y],xs[x+1]-xs[x],ys[y+1]-ys[y]),source,QRectF(ss[x],ss[y],ss[x+1]-ss[x],ss[y+1]-ss[y]))
    painter.restore()


class NeumorphicEffect(QGraphicsEffect):
    def __init__(self,widget,inset=False):
        super().__init__(widget);self.inset=inset;self.motion=None
        if not inset:
            from app.ui.components.tactile_motion import TactileMotion
            kind='primary' if widget.property('accent') or widget.property('role')=='primary' or widget.objectName() in ('detail_play_main','detail_play_arrow') else 'chip' if widget.property('homePill') else 'secondary'
            self.motion=TactileMotion(widget,self.update,kind)
            self.motion.setParent(self)
    def boundingRectFor(self,rect):return rect.adjusted(-PAD,-PAD,PAD,PAD)
    def draw(self,painter):
        if QApplication.instance().property('animevaultHighContrast'):self.drawSource(painter);return
        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.motion:self.motion.transform(painter)
        widget=self.parent();disabled_inset=not widget.isEnabled() and not widget.property('mangaDisabledRaised')
        inset=self.inset or disabled_inset or (isinstance(widget,QAbstractButton) and (widget.isDown() or widget.isChecked() or widget.property('homePill') and widget.property('active')=='true'))
        if self.motion and self.motion.pressed:inset=True
        hover=max(0,min(1,self.motion.hover)) if self.motion else 0
        if not widget.isEnabled() and widget.property('mangaDisabledRaised'):hover=0
        if not inset:
            painter.save();painter.setOpacity(1-hover);paint_depth(painter,widget.rect(),radius=8);painter.restore()
        self.drawSource(painter)
        if inset:paint_depth(painter,widget.rect(),True,radius=8)
        elif hover:
            painter.save();painter.setOpacity(hover);paint_depth(painter,widget.rect(),True,radius=8);painter.restore()
        painter.restore()


def install(widget,inset=False,enabled=True):
    if widget is None:return
    from PyQt5.QtWidgets import QMessageBox
    if isinstance(widget.window(),QMessageBox) or widget.window().property('stableAlert'):enabled=False
    enabled=enabled and not QApplication.instance().property('animevaultHighContrast') and not isinstance(widget,QComboBox)
    effect=widget.graphicsEffect()
    if enabled:
        if not isinstance(effect,NeumorphicEffect) or effect.inset!=inset:widget.setGraphicsEffect(NeumorphicEffect(widget,inset))
    elif isinstance(effect,NeumorphicEffect):widget.setGraphicsEffect(None)


class NeumorphicTrack(QFrame):
    def paintEvent(self,event):
        from app.ui.manga_pages import active
        if not active():super().paintEvent(event);return
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen);painter.setBrush(QColor('#dfe3ed'));painter.drawRoundedRect(QRectF(self.rect()),12,12);paint_depth(painter,self.rect(),True);painter.end()
