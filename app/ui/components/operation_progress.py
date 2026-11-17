"""Shared, truthful circular/bar feedback for foreground disk operations.

Unknown totals stay indeterminate. This observes workers; it never performs IO,
changes cancellation semantics, or manufactures throughput/integrity figures.
"""
import time
from PyQt5 import sip
from PyQt5.QtCore import Qt, QRectF, QTimer, QObject, pyqtSlot
from PyQt5.QtGui import QColor, QPainter, QPen, QFont
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar


class ProgressCircle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = self.total = self.phase = 0
        self.setFixedSize(168, 168)
        self.setAccessibleName('Operation progress')
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._tick)

    def _tick(self):
        if QApplication.instance().property('animevaultReducedMotion'):
            return
        self.phase = (self.phase + 16) % 360
        self.update()

    def set_progress(self, current, total):
        self.total = max(0, int(total))
        self.current = min(max(0, int(current)), self.total) if self.total else 0
        self.setAccessibleDescription(f'{self.current} of {self.total}' if self.total else 'Working; total not yet known')
        if self.total: self.timer.stop()
        elif self.isVisible(): self.timer.start()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.total: self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        from app.ui.home_style import colors
        c = colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ring = QRectF(14, 14, self.width()-28, self.height()-28)
        p.setPen(QPen(QColor(c['raised']), 11, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(ring)
        p.setPen(QPen(QColor(c['coral']), 11, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(ring, (90 if self.total else 90-self.phase)*16,
                  -round(360*16*self.current/self.total) if self.total else -90*16)
        p.setPen(QColor(c['text']))
        font = QFont('Noto Serif', 25 if self.total else 17, QFont.Bold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, f'{round(100*self.current/self.total)}%' if self.total else 'Working')
        p.end()


class OperationProgress(QDialog):
    """Modeless progress card: navigation remains usable while work continues."""
    def __init__(self, owner, title):
        super().__init__(owner, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('operation_progress')
        self.setProperty('animevaultThemeScope', True)
        self.setProperty('animevaultOwnScaledStyle', True)
        self.setWindowTitle(title)
        self.started = time.monotonic()
        self.running = True
        self.current = self.total = 0
        self.setMinimumWidth(540)
        self.resize(620, 590)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        card = ProgressPanel(); card.setObjectName('operation_card')
        outer.addWidget(card)
        box = QVBoxLayout(card); box.setContentsMargins(28, 22, 28, 22); box.setSpacing(16)
        eyebrow = QLabel('●  OPERATION IN PROGRESS  /  処理'); eyebrow.setObjectName('operation_eyebrow')
        box.addWidget(eyebrow)
        self.title = QLabel(title); self.title.setWordWrap(True); self.title.setObjectName('operation_title'); box.addWidget(self.title)
        self.message = QLabel('Preparing operation…'); self.message.setWordWrap(True); box.addWidget(self.message)
        well = ProgressWell(); well.setFixedSize(208,208)
        ring_box = QVBoxLayout(well); ring_box.setContentsMargins(20,20,20,20)
        self.circle = ProgressCircle(); ring_box.addWidget(self.circle)
        box.addWidget(well, 0, Qt.AlignHCenter)
        self.bar = QProgressBar(); self.bar.setTextVisible(False); self.bar.setFixedHeight(12); box.addWidget(self.bar)
        stats = QHBoxLayout()
        self.processed = QLabel('Total not yet known'); self.elapsed = QLabel('0s')
        for caption, value in (('PROCESSED',self.processed),('ELAPSED',self.elapsed),('STATUS',QLabel('Working'))):
            tile = ProgressWell(inset=True); tile_box = QVBoxLayout(tile); tile_box.setContentsMargins(14,12,14,12)
            label = QLabel(caption); label.setObjectName('operation_metric_caption')
            tile_box.addWidget(label); value.setWordWrap(True); tile_box.addWidget(value); stats.addWidget(tile,1)
        box.addLayout(stats)
        note = QLabel('Keep the app open until this operation finishes.'); note.setWordWrap(True); box.addWidget(note)
        self.refresh_home_style()
        self.elapsed_timer = QTimer(self); self.elapsed_timer.timeout.connect(self._elapsed); self.elapsed_timer.start(1000)
        self.report('Preparing operation…', 0, 0)

    def refresh_home_style(self):
        from app.ui.home_style import colors
        from app.ui.manga_pages import active
        c = colors()
        self.setStyleSheet(f'''
            QDialog#operation_progress {{background:transparent;border:none;}}
            QFrame#operation_card {{background:transparent;border:none;}}
            QLabel {{background:transparent;border:none;color:{c['text']};font-size:13px;}}
            QLabel#operation_title {{font-family:"Noto Serif";font-size:25px;font-weight:700;}}
            QLabel#operation_eyebrow {{color:{c['coral']};font-size:11px;font-weight:700;}}
            QLabel#operation_metric_caption {{color:{c['muted']};font-size:10px;font-weight:700;}}
            QProgressBar {{background:{c['raised']};border:1px solid {c['line']};border-radius:6px;}}
            QProgressBar::chunk {{background:{c['coral']};border-radius:5px;}}
        ''')
        self.findChild(QFrame, 'operation_card').update()

    def _elapsed(self):
        self.elapsed.setText(f'{int(time.monotonic()-self.started)}s')

    def report(self, message, current=0, total=0):
        if not self.running: return
        total = max(0, int(total)); current = max(0, min(int(current), total)) if total else 0
        self.current, self.total = current, total
        self.message.setText(str(message)); self.message.setToolTip(str(message))
        self.circle.set_progress(current, total)
        self.bar.setRange(0, total); self.bar.setValue(current)
        self.processed.setText(f'{current:,} / {total:,} processed' if total else 'Total not yet known')

    def finish(self, *args):
        self.running = False
        self.elapsed_timer.stop(); self.circle.timer.stop()
        self.hide()

    def reject(self):
        # No pretend Cancel button: cancellation remains with the actual task.
        if not self.running: super().reject()


class MinorProgress(QObject):
    """Routine work reports to the existing footer, without a new window."""
    def __init__(self, owner, title):
        # A page may be disposed while its cancellation-aware worker finishes.
        # Keep footer cleanup alive until that worker has actually terminated.
        super().__init__(QApplication.instance())
        self.title = title; self.running = True; self.current = self.total = 0
        self.key = f'operation:{id(self)}'
        host = owner
        while host is not None and not hasattr(host, 'refresh_progress'):
            host = host.parentWidget()
        self.sink = getattr(host, 'refresh_progress', None)
        self.report(title)

    def report(self, message, current=0, total=0):
        if not self.running: return
        self.current, self.total = current, total
        if self.sink is not None and not sip.isdeleted(self.sink):
            label = self.title if message == self.title else self.title+' · '+str(message)
            self.sink.report(self.key,current,total,label)

    def finish(self, *args):
        self.running = False
        if self.sink is not None and not sip.isdeleted(self.sink):self.sink.finish(self.key)


def watch(owner, worker, title, progress=None, status=None, order='message_first', *, major=False):
    """Large progress is opt-in at actual major-action sites, never inferred."""
    from PyQt5.QtCore import QThread
    # Headless integrations may reuse action handlers with non-widget adapters.
    if not isinstance(owner, QWidget) or not isinstance(worker, QThread): return None
    dialog = OperationProgress(owner, title) if major else MinorProgress(owner,title)
    if major:
        if not hasattr(owner, '_operation_progress_cards'): owner._operation_progress_cards = []
        owner._operation_progress_cards.append(dialog)
    if progress is not None:
        if order == 'message_first': progress.connect(dialog.report)
        else:
            # QObject-bound adapter, not a worker-thread lambda touching widgets.
            dialog.report_counts = _CountAdapter(dialog)
            progress.connect(dialog.report_counts.report)
    if status is not None:
        dialog.status_adapter = _StatusAdapter(dialog)
        status.connect(dialog.status_adapter.report)
    def cleanup(*args):
        if sip.isdeleted(dialog): return
        dialog.finish()
        if major and not sip.isdeleted(owner) and dialog in owner._operation_progress_cards:
            owner._operation_progress_cards.remove(dialog)
        dialog.deleteLater()
    # Some older workers declare their own finished(dict) signal. Observe both
    # their terminal signals and QThread.finished to cover errors and stops.
    QThread.finished.__get__(worker, type(worker)).connect(cleanup)
    for name in ('failed', 'error', 'stopped'):
        signal = getattr(worker, name, None)
        if signal is not None: signal.connect(cleanup)
    def reveal():
        if sip.isdeleted(dialog) or not dialog.running or not worker.isRunning(): return
        host = owner.window()
        dialog.move(host.frameGeometry().center()-dialog.rect().center())
        dialog.show()
    if major:QTimer.singleShot(180, reveal)
    return dialog


class ProgressPanel(QFrame):
    """Paint the cached shadow directly; no nested offscreen widget effects."""
    def paintEvent(self, event):
        from app.ui.home_style import colors
        from app.ui.manga_pages import active
        c = colors(); p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        face = QRectF(self.rect()).adjusted(12,12,-12,-12)
        if active():
            from app.ui.components.neumorphic import paint_depth
            paint_depth(p, face, radius=24)
        p.setBrush(QColor('#eef0f5' if active() else c['panel']))
        p.setPen(QPen(QColor('#ffffff' if active() else c['line']),1))
        p.drawRoundedRect(face,24,24)
        if QApplication.instance().property('animevaultDecorations') is not False:
            watermark = QColor(c['muted']); watermark.setAlpha(16)
            p.setPen(watermark); p.setFont(QFont('Yu Gothic',48,QFont.Bold))
            p.drawText(face.adjusted(16,8,-16,-8),Qt.AlignTop|Qt.AlignRight,'処理')
        p.end()


class ProgressWell(QFrame):
    def __init__(self, inset=False):
        super().__init__(); self.inset = inset
    def paintEvent(self,event):
        from app.ui.home_style import colors
        from app.ui.manga_pages import active
        c=colors(); p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        face=QRectF(self.rect()).adjusted(2,2,-2,-2)
        p.setPen(QPen(QColor(c['line']),1));p.setBrush(QColor(c['raised'] if self.inset else c['bg']))
        p.drawRoundedRect(face,14,14)
        if active():
            from app.ui.components.neumorphic import paint_depth
            paint_depth(p,face,inset=self.inset,radius=14)
        p.end()


class _CountAdapter(QObject):
    @pyqtSlot(int, int, str)
    def report(self, current, total, message): self.parent().report(message, current, total)


class _StatusAdapter(QObject):
    @pyqtSlot(str)
    def report(self, message):
        dialog = self.parent()
        dialog.report(message, dialog.current, dialog.total)
