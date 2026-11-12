"""Check native maximize/fullscreen using a disposable window, no app data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QLabel
from app.ui.components.title_bar import AppTitleBar
from app.ui.window_chrome import handle_maximize_message


class ProbeWindow(QMainWindow):
    def nativeEvent(self,event_type,message):
        if handle_maximize_message(self,message):return True,0
        return super().nativeEvent(event_type,message)


def main():
    app=QApplication([])
    window=ProbeWindow();window.setProperty('animevaultCustomTitleBar',True)
    window.setWindowTitle('Anime Vault window sizing check');window.resize(1100,720)
    content=QWidget();layout=QVBoxLayout(content);layout.setContentsMargins(0,0,0,0)
    bar=AppTitleBar(window);layout.addWidget(bar);layout.addWidget(QLabel('Temporary window sizing check — closes automatically.'),1)
    window.setCentralWidget(content)
    failures=[]
    def check(mode):
        screen=window.screen();expected=screen.geometry() if mode=='fullscreen' else screen.availableGeometry()
        actual=window.frameGeometry()
        print(mode,'expected',expected.getRect(),'frame',actual.getRect(),'client',window.geometry().getRect(),'maximized',window.isMaximized(),'fullscreen',window.isFullScreen(),flush=True)
        if window.geometry()!=expected:
            failures.append(mode+' did not fill its target area')
        if mode!='fullscreen' and window.isFullScreen():failures.append(mode+' entered fullscreen')
    def fullscreen():
        check('maximized');bar.toggle_fullscreen();QTimer.singleShot(300,restore)
    def restore():
        check('fullscreen');bar.toggle_fullscreen();QTimer.singleShot(300,done)
    def done():
        check('restored-maximized');window.close();app.quit()
    window.show();QTimer.singleShot(300,lambda:(bar.toggle_maximized(),QTimer.singleShot(300,fullscreen)))
    app.exec_()
    if failures:
        print('; '.join(failures));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
