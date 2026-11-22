"""Shared paper surfaces for the second batch of approved Manga light screens."""
from app.ui.manga_style import material
from app.ui.manga_pages import page_qss
from app.ui.home_style import px


def finish(widget):
    """Apply the master control material; never install effects on large views."""
    from PyQt5.QtWidgets import QPushButton,QLineEdit,QComboBox
    from app.ui.manga_pages import active
    from app.ui.components.neumorphic import install
    enabled=active()
    for control in (widget.findChildren(QPushButton)+widget.findChildren(QLineEdit)+widget.findChildren(QComboBox))[:80]:
        install(control,inset=isinstance(control,QLineEdit),enabled=enabled and not control.property('quietAction'))


def qss(name):
    r=f'QWidget#{name}'
    return material(page_qss(name)+f'''
    {r} QWidget#merge_content, {r} QWidget#organizer_clear, {r} QWidget#organizer_cell,
    {r} QWidget#merge_title_cell, {r} QWidget#merge_pill_cell, {r} QWidget#storage_content {{background:transparent;border:none;}}
    {r} QLabel#download_heading, {r} QLabel#storage_heading, {r} QLabel#merge_heading,
    {r} QLabel#organizer_title {{font:800 {px(28)}px 'Noto Serif';color:#111217;}}
    {r} QLabel#storage_panel_title, {r} QLabel#merge_panel_title, {r} QLabel#organizer_section_title {{font:700 {px(19)}px Inter;}}
    {r} QLabel#storage_secondary, {r} QLabel#storage_path, {r} QLabel#merge_hint,
    {r} QLabel#organizer_meta, {r} QLabel#transfer_meta, {r} QLabel#search_label {{color:#596175;font-size:{px(12)}px;}}
    {r} QFrame#transfer_panel, {r} QFrame#organizer_card, {r} QWidget#merge_panel,
    {r} QFrame#storage_panel, {r} QFrame#search_panel, {r} QFrame#release_hero {{background:white;border:1px solid white;border-radius:18px;}}
    {r} QFrame#organizer_row {{background:#eef0f5;border:1px solid white;border-radius:10px;}}
    {r} QFrame#organizer_drop {{background:#f6f7fb;border:2px dashed #c4c9d4;border-radius:16px;}}
    {r} QLabel#organizer_badge, {r} QLabel#merge_pill, {r} QLabel#merge_state,
    {r} QLabel#storage_pill {{color:#596175;background:#e2e5ed;border:1px solid white;border-radius:7px;padding:4px 8px;}}
    {r} QLabel#merge_pill[review='true'], {r} QLabel#storage_pill[tone='warning'] {{color:#805000;background:#fff3cf;}}
    {r} QLabel#storage_pill[tone='success'] {{color:#0e7a4d;background:#e1f4ec;}}
    {r} QLabel#val_label, {r} QLabel#storage_free {{font:800 {px(30)}px 'Noto Serif';}}
    {r} QLabel#val_label[reclaim='true'] {{color:#c4005f;}}
    {r} QLabel#storage_anime_title, {r} QLabel#merge_title {{font-weight:700;}}
    {r} QLabel#storage_caption {{color:#596175;}}
    {r} QTableView, {r} QTableWidget, {r} QListView, {r} QListWidget {{background:#eef0f5;color:#111217;border:1px solid #c4c9d4;border-radius:12px;selection-background-color:#ffe0ef;gridline-color:#e2e5ed;}}
    {r} QTableView::item {{padding:8px;border-bottom:1px solid #e2e5ed;}}
    {r} QHeaderView::section {{background:#e2e5ed;color:#596175;border:none;border-bottom:1px solid #c4c9d4;padding:12px 8px;font:600 {px(11)}px 'JetBrains Mono';}}
    {r} QListWidget::item {{padding:12px;background:#e2e5ed;border:1px solid white;border-radius:8px;margin:4px;}}
    {r} QLineEdit, {r} QComboBox, {r} QSpinBox, {r} QTextEdit {{background:#e2e5ed;color:#111217;border-top:1px solid #aeb7ca;border-left:1px solid #bac1ce;border-right:1px solid white;border-bottom:1px solid white;border-radius:8px;padding:0 12px;}}
    {r} QTextEdit {{padding:12px;}}
    {r} QCheckBox {{background:transparent;color:#111217;spacing:8px;}}
    {r} QCheckBox::indicator {{width:18px;height:18px;border:1px solid #bac1ce;background:white;border-radius:4px;}}
    {r} QCheckBox::indicator:checked {{background:#ff2e93;border-color:#c4005f;}}
    {r} QProgressBar {{background:#e2e5ed;border:1px solid white;border-radius:4px;}}
    {r} QProgressBar::chunk {{background:#ff2e93;}}
    {r} QPushButton[danger='true'], {r} QPushButton#storage_delete {{color:#b3261e;background:#fff1f0;border-color:#f0b4ad;}}
    {r} QLabel#search_status {{background:#e2e5ed;border:1px solid white;border-radius:9px;padding:12px;color:#596175;}}
    QWidget#release_news QFrame#transfer_panel QPushButton {{padding:0 12px;font-size:{px(13)}px;min-height:40px;}}
    {r} QWidget#setup_card {{background:white;border:1px solid white;border-radius:18px;}}
    QWidget#downloads_page QFrame#transfer_panel {{background:transparent;border:none;}}
    QWidget#downloads_page QLabel#download_guide_heading {{font:700 {px(24)}px 'Noto Serif';}}
    QWidget#downloads_page QLabel#download_guide_eyebrow {{font:600 {px(11)}px 'JetBrains Mono';color:#c4005f;}}
    QWidget#downloads_page QTableView {{background:transparent;border:none;}}
    {r} QFrame#search_actions {{background:#eef0f5;border-top:1px solid #c4c9d4;}}
    ''')


def import_qss(name):
    from app.ui.manga_pages import entry_qss
    r=f'QDialog#{name}'
    return material(entry_qss(name)+f'''
    {r} QFrame#import_dropzone {{background:#f6f7fb;border:2px dashed #aeb7ca;border-radius:16px;}}
    {r} QFrame#import_config_card, {r} QFrame#import_switch_card, {r} QFrame#kpi_card,
    {r} QFrame#import_row_card {{background:white;border:1px solid white;border-radius:14px;}}
    {r} QLabel#kpi_value {{font:800 {px(28)}px 'Noto Serif';}}
    {r} QLabel#workflow_row_title {{font-weight:700;}}
    {r} QLabel#workflow_hint {{color:#596175;}}
    ''')
