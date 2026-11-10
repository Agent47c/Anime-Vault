"""Connected additions to the existing settings panels, grouped by task."""
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox,QLineEdit,QListWidget,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView,QLabel
from app import db,preferences
from app.ui.io_task import start


def extend_settings(page):
    from app.ui.downloads import DownloadsDrawer
    from app.ui.download_setup import open_setup
    column=page._tab_layouts['Downloads & Sources']
    guide=page._button('Set up downloads step by step',lambda:open_setup(page),True)
    column.insertWidget(0,guide)
    config=DownloadsDrawer(page,settings_only=True)
    config._embedded=True;config.setWindowFlags(Qt.Widget);config.setMinimumWidth(0);config.setMinimumHeight(650)
    config.setProperty('animevaultThemeScope',True)
    page.download_config=config
    column.insertWidget(column.count()-1,config)

    from app.core import download_discovery
    panel,box=page._panel('Sources')
    table=QTableWidget(0,2);table.setHorizontalHeaderLabels(['Source name','Search URL — include {query}'])
    table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
    table.verticalHeader().hide();table.setMinimumHeight(180);table.setWordWrap(False)
    def add_source(name='New source',url='https://example.org/?q={query}'):
        row=table.rowCount();table.insertRow(row)
        table.setItem(row,0,QTableWidgetItem(name));table.setItem(row,1,QTableWidgetItem(url))
    for source in download_discovery.sources(): add_source(source['name'],source['url'])
    box.addWidget(table)
    source_status=QLabel('The extension needs permission for the source you select. Nyaa-style tables and generic magnet rows are supported.');source_status.setWordWrap(True);box.addWidget(source_status)
    box.addWidget(page._button('Add source',lambda:add_source()))
    box.addWidget(page._button('Remove selected source',lambda:table.removeRow(table.currentRow()) if table.currentRow()>=0 else None))
    def save_sources():
        rows=[dict(name=table.item(i,0).text() if table.item(i,0) else '',url=table.item(i,1).text() if table.item(i,1) else '') for i in range(table.rowCount())]
        index=table.currentRow()
        def save():
            download_discovery.save_sources(rows)
            if index>=0:
                from app.core.downloads import save_settings
                save_settings({'source':rows[index]['url']})
        def done(_):
            source_status.setText('Sources saved. Highlighted source is the default. Enable that website in the Chrome popup.')
            if index>=0: config.controls['source'].setText(rows[index]['url'])
        start(page,save,done)
    box.addWidget(page._button('Save sources / use highlighted',save_sources,True))
    column.insertWidget(column.count()-1,panel)

    panel,box=page._panel('Watchers and automatic imports')
    page._toggle(box,'Watch library folders','Detect changes in configured roots and indexed season folders. Changes trigger a debounced local scan.','folder_watchers')
    page._toggle(box,'Watch TXT import lists','Check enabled lists once a minute. New names become custom entries needing review; no weak API matches are applied.','list_watchers')
    subscriptions=QListWidget();subscriptions.setMinimumHeight(140);box.addWidget(subscriptions)
    def render():
        from app.core.import_lists import lists
        subscriptions.clear()
        for row in lists():
            subscriptions.addItem(('On · ' if row.get('enabled') else 'Off · ')+row['path']+' · '+row.get('status','WATCHED')+(' · '+row['error'] if row.get('error') else ''))
    def add_list():
        path,_=QFileDialog.getOpenFileName(page,'Watch a TXT list','','Text files (*.txt)')
        if not path:return
        from app.core.import_lists import lists,save
        rows=lists()
        if any(Path(row['path'])==Path(path) for row in rows): return
        rows.append(dict(path=path,enabled=False,status='WATCHED'));save(rows);render()
    def update_list(remove=False):
        from app.core.import_lists import lists,save
        rows=lists();index=subscriptions.currentRow()
        if index<0:return
        if remove: rows.pop(index)
        else: rows[index]['enabled']=not rows[index].get('enabled')
        save(rows);render()
    box.addWidget(page._button('Add TXT list',add_list))
    box.addWidget(page._button('Enable / disable selected list',lambda:update_list()))
    box.addWidget(page._button('Remove selected list',lambda:update_list(True)))
    import_status=QComboBox()
    for label,key in [('Watched','WATCHED'),('Watching','WATCHING'),('Plan to watch','PLAN_TO_WATCH'),('Dropped','DROPPED')]: import_status.addItem(label,key)
    def set_status():
        from app.core.import_lists import lists,save
        rows=lists();index=subscriptions.currentRow()
        if index>=0:
            rows[index]['status']=import_status.currentData();rows[index].pop('digest',None);save(rows);render()
    page._row(box,'Status for selected list','Choose status, then apply it to the highlighted subscription.',import_status)
    box.addWidget(page._button('Apply list status',set_status))
    def check_lists():
        from app.core.import_lists import refresh
        start(page,lambda:refresh(force=True),lambda _: (render(),page.scan_completed.emit()))
    box.addWidget(page._button('Check enabled lists now',check_lists))
    page._tab_layouts['Watchers & Import Lists'].insertWidget(0,panel);render()

    panel,box=page._panel('Naming and organization rules')
    from app.ui.components.settings_switch import SettingsSwitch
    for key,label in [('detect_season_names','Detect season/part names'),('detect_episode_numbers','Detect episode numbers'),('keep_subtitles_fonts','Keep subtitles and fonts with episodes')]:
        control=SettingsSwitch(db.get_state('organizer.rule:'+key,'1')=='1')
        control.toggled.connect(lambda checked,name=key: (db.set_state('organizer.rule:'+name,'1' if checked else '0'),page.preferences_changed.emit()))
        page._row(box,label,'Applies to the next organizer preview.',control)
    def open_organizer():
        host=page.window()
        if hasattr(host,'_on_nav_clicked'): host._on_nav_clicked(1)
    box.addWidget(page._button('Open organizer and preview file changes',open_organizer))
    col=page._tab_layouts['Scanning & Organization'];col.insertWidget(col.count()-1,panel)

    panel,box=page._panel('Playback, audio and subtitles')
    controls=[]
    for key,label,options in [('playback.fullscreen','Open player full screen',[('Off','0'),('On','1')]),
                              ('playback.subtitles','Subtitles',[('Enabled','1'),('Disabled','0')]),
                              ('playback.slang','Preferred subtitle language',[('Player default',''),('English','eng'),('Japanese','jpn')]),
                              ('playback.alang','Preferred audio language',[('Player default',''),('Japanese','jpn'),('English','eng')])]:
        combo=QComboBox()
        for name,value in options: combo.addItem(name,value)
        combo.setCurrentIndex(max(0,combo.findData(db.get_state(key,options[0][1]))))
        combo.currentIndexChanged.connect(lambda _,name=key,c=combo:db.set_state(name,c.currentData()))
        page._row(box,label,'Applied to VLC and MPV. Other players use their own preferences.',combo);controls.append(combo)
    def player_changed():
        for control in controls: control.setEnabled(page.player_combo.currentData() in ('vlc','mpv'))
    page.player_combo.currentIndexChanged.connect(player_changed);player_changed()
    col=page._tab_layouts['Media Player'];col.insertWidget(col.count()-1,panel)

    panel,box=page._panel('Backup location and maintenance')
    backup=QLineEdit(db.get_state('backup_directory',str(db.DATA_DIR/'backups')));backup.setReadOnly(True)
    page._row(box,'Backup folder','SQLite backups include committed WAL data.',backup)
    def choose_backup():
        folder=QFileDialog.getExistingDirectory(page,'Choose backup folder',backup.text())
        if folder: db.set_state('backup_directory',folder);backup.setText(folder)
    box.addWidget(page._button('Choose backup folder',choose_backup))
    maintenance=QLabel('Check database integrity and checkpoint the write-ahead log.');maintenance.setWordWrap(True);box.addWidget(maintenance)
    def check_database():
        from contextlib import closing
        def check():
            with closing(db.get_connection()) as conn:
                result=conn.execute('PRAGMA quick_check').fetchone()[0]
                conn.execute('PRAGMA wal_checkpoint(PASSIVE)')
            return 'Database check: '+result
        start(page,check,maintenance.setText)
    box.addWidget(page._button('Check and maintain database',check_database))
    col=page._tab_layouts['Database & Backup'];col.insertWidget(col.count()-1,panel)
