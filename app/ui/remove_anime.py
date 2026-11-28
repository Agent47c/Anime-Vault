"""Explicit library removal with optional existing Recycle Bin review."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from app.ui.components.message_boxes import AppMessageBox as QMessageBox
from app import db
from app.core.library_removal import removal_context,remove_entry
from app.ui.io_task import start
from app.ui.navigation import navigate

def open_remove_anime(parent,fid,removed=None):
    try:series,members,seasons=removal_context(fid)
    except ValueError as error:QMessageBox.information(parent,'Remove anime',str(error));return
    prompt=QMessageBox(QMessageBox.Question, 'Remove anime?',
                       'Remove '+series['display_title']+' from your library?', parent=parent)
    prompt.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    prompt.setInformativeText('Remove the entry and keep your local files, or review which indexed videos would go to the Recycle Bin. Both options include seasons grouped under this anime.')
    prompt.actions.setOrientation(Qt.Vertical)
    keep=prompt.addButton('Remove entry only',QMessageBox.AcceptRole)
    delete=prompt.addButton('Review file removal',QMessageBox.DestructiveRole)
    cancel=prompt.addButton(QMessageBox.Cancel)
    prompt.setDefaultButton(cancel)
    prompt.exec_()
    choice=prompt.clickedButton()
    prompt.deleteLater()
    def done(message):
        if removed:removed()
        from app.ui.downloads import monitor
        monitor().changed.emit()
    if choice is keep:start(parent,lambda:remove_entry(fid),done)
    elif choice is delete:
        from app.ui.dialogs.delete_confirm import DeleteConfirmDialog
        remaining=list(members)
        def next_member():
            if not remaining:start(parent,lambda:remove_entry(fid,True),done);return
            member=remaining.pop(0);owned=[s for s in seasons if s['franchise_id']==member and s.get('storage_state')=='ON_DISK']
            if not owned:next_member();return
            dialog=DeleteConfirmDialog(db.get_franchise(member),owned,parent)
            if not dialog.total_files:QMessageBox.warning(parent,'Files unavailable','This anime has unavailable local files. Reconnect the drive and try again, or choose to keep files.');return
            def finished(result):
                if result==QDialog.Accepted and not getattr(dialog,'result_details',{}).get('failures'):next_member()
            navigate(dialog,finished)
        next_member()
