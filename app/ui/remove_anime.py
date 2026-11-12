"""Explicit library removal with optional existing Recycle Bin review."""
from PyQt5.QtWidgets import QMessageBox,QDialog
from app import db
from app.core.library_removal import removal_context,remove_entry
from app.ui.io_task import start
from app.ui.navigation import navigate

def open_remove_anime(parent,fid,removed=None):
    try:series,members,seasons=removal_context(fid)
    except ValueError as error:QMessageBox.information(parent,'Remove anime',str(error));return
    prompt=QMessageBox(parent);prompt.setWindowTitle('Remove anime?');prompt.setText('Remove '+series['display_title']+' from your library?');prompt.setInformativeText('Choose whether to keep your local files or review moving indexed videos to the Recycle Bin. This includes the seasons grouped under this anime.')
    keep=prompt.addButton('Remove entry — keep files',QMessageBox.AcceptRole);delete=prompt.addButton('Delete files and remove entry',QMessageBox.DestructiveRole);cancel=prompt.addButton(QMessageBox.Cancel);prompt.setDefaultButton(cancel);prompt.exec_()
    choice=prompt.clickedButton()
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
