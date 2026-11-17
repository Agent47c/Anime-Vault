"""Twelve additional references, using the existing Manga master materials."""
from app.ui.manga_workflows import qss as workflow_qss
from app.ui.home_style import px


def qss(name):
    r=f'QWidget#{name}'
    modal=name in ('season_numbers','group_review','adult_access','quit_dialog','confirm_selected')
    return workflow_qss(name)+f'''
    {r} {{background:{'white' if modal else '#eef0f5'};color:#111217;}}
    {r} QLabel#heading, {r} QLabel#dialog_title, {r} QLabel#duplicate_heading,
    {r} QLabel#settings_heading {{font:800 {px(28)}px 'Noto Serif';color:#111217;}}
    {r} QLabel#dialog_subtitle, {r} QLabel#settings_subtitle, {r} QLabel#settings_hint {{color:#596175;}}
    {r} QFrame#workflow_header, {r} QFrame#workflow_footer {{background:{'white' if modal else '#eef0f5'};border:none;}}
    {r} QFrame#workflow_card, {r} QFrame#transfer_panel, {r} QFrame#merge_panel,
    {r} QFrame#duplicate_stat, {r} QFrame#settings_panel, {r} QFrame#settings_navigation,
    {r} QFrame#playback_footer {{background:white;border:1px solid white;border-radius:14px;}}
    {r} QFrame#workflow_card[primary='true'], {r} QFrame#quit_choice[selected='true'] {{border:2px solid #ff2e93;}}
    {r} QFrame#quit_choice {{background:#f3f4f8;border:1px solid white;border-radius:14px;}}
    {r} QLabel#group_anchor, {r} QLabel#season_notice, {r} QLabel#episode_availability,
    {r} QLabel#workflow_hint[notice='true'] {{background:#e2e5ed;border:1px solid white;border-radius:10px;padding:12px;}}
    {r} QLabel#group_badge, {r} QLabel#season_badge {{background:#eef0f5;color:#596175;border:1px solid white;border-radius:5px;padding:4px 8px;font-size:{px(11)}px;}}
    {r} QLabel#group_anchor {{color:#805000;}}
    {r} QLabel#duplicate_value {{font:800 {px(28)}px 'Noto Serif';}}
    {r} QLineEdit, {r} QSpinBox {{background:#e2e5ed;color:#111217;border:1px solid #c4c9d4;border-radius:8px;}}
    {r} QSpinBox {{font:700 {px(17)}px Inter;padding:0 10px;min-height:40px;}}
    {r} QTreeWidget {{background:transparent;color:#111217;border:none;alternate-background-color:transparent;}}
    {r} QTreeWidget::item {{background:white;color:#111217;border-bottom:1px solid #e2e5ed;padding:10px;}}
    {r} QTreeWidget::item:selected {{background:#ffe0ef;}}
    {r} QTreeWidget::indicator:checked {{background:#ff2e93;border:1px solid #c4005f;}}
    {r} QHeaderView::section {{background:#eef0f5;color:#596175;border:none;padding:12px 8px;}}
    {r} QListView#episode_grid, {r} QListView#group_series_choices {{background:transparent;border:none;outline:none;}}
    {r} QListView#group_series_choices::item {{background:white;border:1px solid white;border-radius:12px;margin:5px;padding:12px;}}
    {r} QListView#group_series_choices::item:selected {{border:2px solid #ff2e93;background:#fff8fc;}}
    {r} QLabel#dialog_error, {r} QLabel#quit_warning {{color:#b3261e;}}
    {r} QLabel#adult_kicker {{font:600 {px(11)}px Inter;color:#596175;}}
    {r} QRadioButton::indicator {{border-radius:10px;}}
    {r} QCheckBox, {r} QRadioButton {{background:transparent;color:#111217;spacing:10px;min-height:30px;}}
    {r} QCheckBox::indicator, {r} QRadioButton::indicator {{width:20px;height:20px;background:#f6f7fb;border:2px solid #596175;}}
    {r} QCheckBox::indicator:checked, {r} QRadioButton::indicator:checked {{background:#ff2e93;border-color:#c4005f;}}
    {r} QLabel#workflow_match[tone='warning'] {{background:#fff3cf;color:#805000;}}
    {r} QWidget#settings_navigation {{min-width:270px;}}
    QWidget#confirm_selected QFrame#workflow_card {{background:#f6f7fb;border:1px solid #e2e5ed;}}
    {r} QWidget#settings_content, {r} QTabWidget#settings_tabs::pane {{background:transparent;border:none;}}
    {r} QFrame#settings_panel, {r} QFrame#settings_navigation {{background:transparent;border:none;padding:0;}}
    {r} QLabel#settings_panel_title {{font:700 {px(21)}px 'Noto Serif';}}
    {r} QLabel#settings_panel_code {{font:600 {px(10)}px 'JetBrains Mono';color:#c4005f;}}
    {r} QWidget#settings_row, {r} QWidget#settings_choices, {r} QScrollArea>QWidget {{background:transparent;border:none;}}
    {r} QFrame#settings_segments {{background:#e2e5ed;border:1px solid white;border-radius:10px;}}
    {r} QFrame#settings_divider {{background:#e2e5ed;border:none;}}
    {r} QPushButton[settingsSection='true'] {{text-align:left;}}
    {r} QPushButton[settingsSection='true']:checked {{background:#ffe0ef;color:#c4005f;border-color:#ff2e93;}}
    {r} QPushButton#settings_theme_card {{min-height:{px(170)}px;max-height:{px(170)}px;padding:0;}}
    {r} QPushButton[settingsPlayerCard='true'] {{min-height:{px(70)}px;}}
    '''
