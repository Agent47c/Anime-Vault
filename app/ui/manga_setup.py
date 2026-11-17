"""Single-screen layout adapter around the existing five setup operations."""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget,QGridLayout,QLabel,QPushButton,QSizePolicy,QVBoxLayout,QHBoxLayout


def configure(dialog,active):
    if active==getattr(dialog,'_manga_setup_active',False):return
    dialog._manga_setup_active=active
    if active:
        dialog.full_page=True
        dialog._setup_pages=[dialog.stack.widget(i) for i in range(dialog.stack.count())]
        panel=QWidget();panel.setObjectName('workflow_field');grid=QGridLayout(panel);grid.setSpacing(24);dialog._setup_grid=grid;dialog._setup_panel=panel
        index=dialog._setup_body.indexOf(dialog.stack);dialog._setup_body.insertWidget(index,panel)
        strip=QWidget();strip.setObjectName('setup_status_strip');line=QGridLayout(strip);line.setContentsMargins(0,6,0,6);line.setSpacing(12);dialog._setup_statuses=[];dialog._setup_status_strip=strip
        for name in ('Extension','Engine','Folder','Sources','Finish'):
            label=QLabel();label.setWordWrap(True);line.addWidget(label,0,len(dialog._setup_statuses));dialog._setup_statuses.append(label)
        dialog._setup_body.insertWidget(index,strip);dialog.overview.hide();update_steps(dialog)
        from app.ui.components.paper_card import PaperCard
        dialog._setup_wrappers=[];dialog._setup_button_states=[]
        for i,page in enumerate(dialog._setup_pages):
            dialog.stack.removeWidget(page);page.setObjectName('setup_card')
            title=QLabel(f'Step {i+1} of 5 · {dialog.titles[i]}');title.setObjectName('workflow_row_title');page.layout().insertWidget(0,title);page._manga_step_title=title
            wrapper=PaperCard();wrapper.setObjectName('setup_depth');wrapper.setStyleSheet('QFrame#setup_depth{background:transparent;border:none;}');frame=QVBoxLayout(wrapper);frame.setContentsMargins(10,10,10,10);frame.addWidget(page);dialog._setup_wrappers.append(wrapper)
            page.layout().setContentsMargins(22,22,22,22);grid.addWidget(wrapper,i if i<3 else i-3,0 if i<3 else 1);page.show()
            from PyQt5.QtCore import Qt
            for control in page.findChildren(QPushButton):
                layout=control.parentWidget().layout();item=layout.itemAt(layout.indexOf(control)) if layout and layout.indexOf(control)>=0 else None
                dialog._setup_button_states.append((control,control.sizePolicy(),layout,item.alignment() if item else Qt.Alignment()))
                control.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
                if control.parentWidget().layout():control.parentWidget().layout().setAlignment(control,Qt.AlignLeft)
        dialog.stack.hide();dialog.progress.hide();dialog.next_button.clicked.disconnect();dialog.next_button.clicked.connect(dialog.test_all_steps);dialog.next_button.setText('Test connections && finish')
    else:
        for control,policy,layout,alignment in dialog._setup_button_states:
            control.setSizePolicy(policy)
            if layout:layout.setAlignment(control,alignment)
        for page,wrapper in zip(dialog._setup_pages,dialog._setup_wrappers):
            dialog._setup_grid.removeWidget(wrapper);wrapper.layout().removeWidget(page);page._manga_step_title.deleteLater();page.setObjectName('workflow_field');page.layout().setContentsMargins(0,0,0,0);dialog.stack.addWidget(page);wrapper.deleteLater()
        dialog._setup_panel.hide();dialog._setup_panel.deleteLater();dialog.stack.show();dialog.progress.show();dialog.stack.setCurrentIndex(dialog.step)
        dialog._setup_status_strip.deleteLater();dialog.overview.show()
        dialog.next_button.clicked.disconnect();dialog.next_button.clicked.connect(dialog.advance)


def arrange(dialog):
    if not getattr(dialog,'_manga_setup_active',False):return
    narrow=dialog.width()<1100
    for i,wrapper in enumerate(dialog._setup_wrappers):dialog._setup_grid.addWidget(wrapper,i if narrow or i<3 else i-3,0 if narrow or i<3 else 1)
    columns=5 if not narrow else 2 if dialog.width()>=650 else 1
    for i,label in enumerate(dialog._setup_statuses):dialog._setup_status_strip.layout().addWidget(label,i//columns,i%columns)


def update_steps(dialog):
    from app.ui.home_style import px
    for i,(label,name,state) in enumerate(zip(dialog._setup_statuses,('Extension','Engine','Folder','Sources','Finish'),dialog.steps)):
        label.setText(f'{i+1:02}  {name}\n{state}')
        label.setStyleSheet(f'background:#e2e5ed;color:#111217;border:1px solid {"#ff2e93" if i==dialog.step else "white"};border-radius:10px;padding:{px(12)}px;font-size:{px(12)}px;')
