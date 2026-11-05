"""
Automatic Windows Dark/Light mode QSS theme engine.
Faithfully recreates the visual design from the Anime Manager UI Reference mockups.
"""

import re
from string import Template
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

# ---------------------------------------------------------------------------
# Color Palette (Matching UI Reference Mockups)
# ---------------------------------------------------------------------------
COLORS = {
    "dark": {
        "bg_primary": "#0d0e12",          # Main window canvas
        "bg_secondary": "#12141b",        # Sidebar and top header
        "bg_card": "#171a23",             # Surface cards, hero banners, modal
        "bg_card_alt": "#1e222e",         # Sub-cards, season rows
        "bg_hover": "#1e2230",            # Hover state
        "bg_input": "#11131a",            # Search and text fields
        "bg_modal": "#171a23",            # Dialog background
        "accent": "#ec2349",              # Magenta anime accent
        "accent_hover": "#ef3b59",
        "accent_secondary": "#8a2be2",    # Purple accent
        "accent_gradient_start": "#431238",
        "accent_gradient_end": "#b8235a",
        "text_primary": "#f3f4f6",        # Clean white
        "text_secondary": "#9ca3af",      # Muted slate
        "text_muted": "#898d9f",          # Subdued hint text
        "border": "#2a2e3a",              # Sleek border
        "border_light": "#383d4c",
        "border_focus": "#ec2349",
        "success": "#22c55e",
        "success_bg": "rgba(34, 197, 94, 0.15)",
        "warning": "#f59e0b",
        "warning_bg": "rgba(245, 158, 11, 0.15)",
        "danger": "#ef4444",
        "danger_bg": "rgba(239, 68, 68, 0.15)",
        "info": "#3b82f6",
        "pill_dark": "#1e2230",
        "scrollbar": "#1e2230",
        "scrollbar_hover": "#2e3447",
        "shadow": "rgba(0, 0, 0, 0.5)",
    },
    "light": {
        "bg_primary": "#f4f5f8",
        "bg_secondary": "#ffffff",
        "bg_card": "#ffffff",
        "bg_card_alt": "#f8f9fc",
        "bg_hover": "#f1f3f7",
        "bg_input": "#f9fafb",
        "bg_modal": "#ffffff",
        "accent": "#ec2349",
        "accent_hover": "#cc206a",
        "accent_secondary": "#8a2be2",
        "accent_gradient_start": "#431238",
        "accent_gradient_end": "#b8235a",
        "text_primary": "#111827",
        "text_secondary": "#4b5563",
        "text_muted": "#9ca3af",
        "border": "#e5e7eb",
        "border_light": "#d1d5db",
        "border_focus": "#ec2349",
        "success": "#16a34a",
        "success_bg": "rgba(22, 163, 74, 0.12)",
        "warning": "#d97706",
        "warning_bg": "rgba(217, 119, 6, 0.12)",
        "danger": "#dc2626",
        "danger_bg": "rgba(220, 38, 38, 0.12)",
        "info": "#2563eb",
        "pill_dark": "#e5e7eb",
        "scrollbar": "#d1d5db",
        "scrollbar_hover": "#9ca3af",
        "shadow": "rgba(0, 0, 0, 0.08)",
    },
}


for palette, values in (
    ("dark", ("#0B0C10", "#14161D", "#1C1F29", "rgba(255,255,255,0.12)", "#F2F3F7", "#B4B9CA", "#8E94A8", "#8B8CFF", "#C4C5FF", "#FF7083", "#5ED6A0", "#F2B94B", "#FF8A8A", "rgba(20,22,29,0.72)")),
    ("light", ("#F5F5F7", "#FFFFFF", "#ECECF1", "rgba(0,0,0,0.14)", "#1D1D1F", "#4A4A55", "#62626D", "#4B4DD6", "#2E30B8", "#B3122D", "#0E7A4D", "#8A5A00", "#B3261E", "rgba(255,255,255,0.72)")),
):
    roles = ("bg_primary", "bg_card", "bg_card_alt", "border", "text_primary", "text_secondary",
             "text_muted", "accent_secondary", "border_focus", "red_text", "success", "warning", "danger", "glass")
    COLORS[palette].update(zip(roles, values))
    COLORS[palette].update(accent="#D92D45", accent_hover="#E5384F", on_red="#FFFFFF", accent_tint="rgba(217,45,69,0.12)")


_SHELL_QSS = Template("""
QFrame#sidebar { background: $glass; border-right: 1px solid $border; }
QFrame#top_bar, QFrame#status_bar { background: $bg_primary; }
QFrame#top_bar { border: none; }
QPushButton#toolbar_refresh { padding: 0 30px 0 14px; }
QPushButton#organizer_review { min-width: 68px; min-height: 40px; padding: 0 16px;
    background: $bg_card_alt; color: $text_primary; border: 2px solid $border;
    border-radius: 10px; font-size: 14px; font-weight: 600; }
QPushButton#organizer_review:hover { background: $bg_hover; border-color: $accent_secondary; }
QPushButton#organizer_review:pressed { background: $bg_hover; border-color: $accent_secondary; }
QPushButton#organizer_review:focus { border: 2px solid $border_focus; }
QFrame#status_bar { border-top: 1px solid $border; }
QFrame#shell_nav, QFrame#collection_row { background: transparent; border-radius: 10px; }
QFrame#shell_nav:hover, QFrame#shell_nav[active="true"], QFrame#collection_row:hover { background: $bg_card_alt; }
QFrame#shell_nav:focus, QFrame#collection_row:focus { border: 2px solid $border_focus; }
QLabel#nav_text { color: $text_secondary; font-size: 16px; }
QFrame#shell_nav[active="true"] QLabel#nav_text { color: $text_primary; font-weight: 600; }
QLabel#brand_mark, QLabel#nav_badge_2 { background: $accent; color: $on_red; font-weight: 700; }
QLabel#brand_mark { border-radius: 10px; font-size: 18px; }
QLabel#nav_badge_2 { border-radius: 12px; padding: 0 7px; font-size: 12px; }
QLabel#brand_title { font-size: 17px; font-weight: 700; }
QLabel#shell_caption { color: $text_muted; font-size: 12px; font-weight: 600; }
QLabel#shell_muted { color: $text_secondary; font-size: 13px; }
QLabel#drive_free { color: $red_text; font-size: 20px; font-weight: 700; }
QLabel#storage_link { color: $accent_secondary; text-decoration: underline; font-size: 13px; }
QFrame#sidebar_drive_card, QFrame#shell_search { background: $bg_card; border: 1px solid $border; border-radius: 12px; }
QProgressBar#sidebar_drive_bar { background: $bg_card_alt; border: none; border-radius: 4px; }
QProgressBar#sidebar_drive_bar::chunk { background: $accent; border-radius: 4px; }
QLabel#api_dot[available="true"] { background: $success; border-radius: 4px; }
QLabel#api_dot[available="false"] { background: $text_muted; border-radius: 4px; }
QPushButton#task_banner { background: $warning_bg; color: $warning; padding: 8px 16px; text-align: left; }
QFrame#final_panel[today="true"] {
    border: 2px solid $accent;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(217,45,69,0.16), stop:1 $bg_card);
}
QLabel#airing_kanji { color: $text_muted; font-size: 18px; }
QPushButton#airing_release { padding: 4px; font-size: 13px; }
QPushButton#entry_rating { padding: 0; border-radius: 8px; }
QPushButton#entry_rating:checked { background: $accent_secondary; color: $on_indigo; }
QListWidget { background: $bg_card; border: 1px solid $border; border-radius: 12px; }
QListWidget::item { min-height: 36px; padding: 4px 8px; }
QListWidget::item:selected { background: $bg_card_alt; color: $text_primary; }
QCheckBox::indicator, QListWidget::indicator {
    width: 16px; height: 16px; border: 2px solid $text_muted;
    border-radius: 5px; background: $bg_card;
}
QCheckBox::indicator:checked, QListWidget::indicator:checked {
    border: 2px solid $accent_secondary; background: $accent_secondary;
}
QWidget#entry_form_body, QDialog#entry_drawer { background: $bg_card; }
QWidget#entry_form_body QGroupBox {
    background: $bg_card; border: 1px solid $border; border-radius: 16px;
    margin-top: 20px; padding: 20px 16px 16px;
}
QWidget#entry_form_body QGroupBox::title { background: $bg_card; color: $text_primary; padding: 0 6px; }
QWidget#entry_form_body QLineEdit, QWidget#entry_form_body QTextEdit, QWidget#entry_form_body QComboBox {
    background: $bg_primary; color: $text_primary; border: 1px solid $border; border-radius: 12px;
}
QLabel#airing_title { font-size: 14px; font-weight: 600; color: $text_primary; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: $text_muted; min-width: 36px; border-radius: 5px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; background: transparent; }
QComboBox::drop-down { width: 28px; border: none; }
QComboBox::down-arrow { image: url("$chevron"); width: 16px; height: 16px; border: none; margin: 0; }
QPushButton::menu-indicator { image: url("$chevron"); width: 16px; height: 16px; subcontrol-position: right center; right: 8px; }
QWidget#workflow_panel, QDialog#workflow_dialog, QDialog#entry_drawer { background: $bg_card; }
QWidget#workflow_panel { border: 1px solid $border; border-radius: 18px; }
QWidget#entry_form_body > QWidget { background: transparent; }
QLabel#section_chip { background: $accent; color: $on_red; border-radius: 6px; padding: 0 7px; font-size: 12px; font-weight: 700; }
QLabel#library_heading { color: $text_primary; font-size: 22px; font-weight: 700; }
QFrame#detail_table { background: $bg_card; border: 1px solid $border; border-radius: 16px; }
QFrame#detail_table QLabel { background: transparent; }
QFrame#detail_table QPushButton { padding: 5px 10px; min-height: 26px; }
QDialog#series_details, QWidget#detail_content { background: $bg_primary; border: none; }
QLabel#detail_badge { background: $bg_card_alt; border: 1px solid $border; color: $text_primary;
    border-radius: 11px; padding: 3px 10px; font-size: 12px; font-weight: 600; }
QLabel#detail_badge[airing="true"] { border-color: $red_text; color: $red_text; }
QFrame#watch_status_track { background: transparent; border: none; }
QPushButton#watch_status_option { background: $bg_card_alt; color: $text_secondary; border: 1px solid $border; padding: 0 18px; min-height: 40px; border-radius: 10px; }
QPushButton#watch_status_option:checked { background: $text_primary; color: $bg_primary; }
QFrame#detail_table QWidget { background: transparent; }
QFrame#detail_table { padding: 0; }
QFrame#detail_delete_panel { background: $bg_card; border: 1px solid $border; border-radius: 14px; }
QFrame#detail_play_split { background: $accent; border: none; border-radius: 12px; }
QPushButton#detail_play_main, QPushButton#detail_play_arrow {
    background: $accent; color: $on_red; border: none; border-radius: 0; font-size: 13px; font-weight: 600;
}
QPushButton#detail_play_main { border-top-left-radius: 12px; border-bottom-left-radius: 12px; padding: 0 16px; }
QPushButton#detail_play_arrow { border-left: 1px solid rgba(255,255,255,0.35);
    border-top-right-radius: 12px; border-bottom-right-radius: 12px; padding: 0; }
QPushButton#detail_play_main:hover, QPushButton#detail_play_arrow:hover { background: $accent_hover; }
QMenu#detail_play_menu { background: $bg_card; border: 1px solid $border; border-radius: 12px; padding: 8px; }
QMenu#detail_play_menu::item { min-height: 24px; padding: 8px 10px; color: $text_primary; border-radius: 6px; }
QMenu#detail_play_menu::item:selected { background: $accent_secondary; color: $on_indigo; }
QMenu#detail_play_menu::item:disabled { color: $text_muted; }
QListView#episode_grid { background: $bg_primary; border: none; outline: none; }
QPushButton#airing_count { background: $bg_card_alt; border: 1px solid $border; border-radius: 12px; padding: 0; }
QPushButton#airing_count:hover { border-color: $red_text; }
QPushButton#airing_count:disabled { background: transparent; border: 1px solid transparent; }
QLabel#airing_number { color: $red_text; font-size: 26px; font-weight: 800; background: transparent; }
QFrame#airing_preview { background: $bg_card_alt; border: 1px solid $border; border-radius: 12px; }
QLabel#airing_preview_title { color: $text_primary; font-size: 13px; font-weight: 600; }
QLabel#airing_preview_poster { background: $bg_card_alt; border-radius: 5px; }
QLabel#episode_availability { background: $bg_card; border: 1px solid $border; border-radius: 12px; padding: 12px 16px; color: $text_secondary; }
QWidget#airing_preview_content, QScrollArea#airing_preview_scroll, QScrollArea#airing_preview_scroll > QWidget { background: $bg_card_alt; border: none; }
QPushButton#airing_preview_item, QPushButton#airing_preview_item:hover, QPushButton#airing_preview_item:pressed {
    background: $bg_card_alt; color: $text_primary; border: none; border-radius: 8px; padding: 0;
}
QPushButton#airing_preview_item QLabel { background: transparent; border: none; }
QPushButton#clear_search { background: transparent; border: none; border-radius: 8px; padding: 0; color: $text_secondary; font-size: 22px; }
QPushButton#clear_search:hover { background: $bg_card_alt; color: $text_primary; }
QFrame#storage_panel { background: $bg_card; border: 1px solid $border; border-radius: 18px; }
QWidget#storage_content { background: $bg_primary; }
QWidget#storage_page QLabel#storage_heading { font-size: 34px; font-weight: 800; }
QWidget#storage_page QLabel#storage_panel_title { font-size: 18px; font-weight: 700; }
QWidget#storage_page QLabel#storage_secondary { font-size: 16px; color: $text_secondary; }
QWidget#storage_page QLabel#storage_free { font-size: 44px; font-weight: 800; color: $red_text; }
QWidget#storage_page QLabel#val_label { font-size: 32px; font-weight: 800; }
QWidget#storage_page QLabel#val_label[reclaim="true"] { color: $red_text; }
QWidget#storage_page QLabel#storage_caption { font-size: 13px; color: $text_secondary; }
QTableWidget#storage_table { background: $bg_card; border: none; }
QTableWidget#storage_table::item { border: none; border-bottom: 1px solid $border; padding: 0; }
QTableWidget#storage_table QWidget { background: transparent; }
QWidget#storage_page QPushButton#storage_open { background: $bg_card_alt; border: 1px solid $border; }
QTableWidget#storage_table QHeaderView::section { background: $bg_card; color: $text_muted; font-size: 12px; font-weight: 600; border: none; border-bottom: 1px solid $border; padding: 0 8px; }
QWidget#storage_page QLabel#storage_anime_title { font-size: 14px; font-weight: 700; }
QWidget#storage_page QLabel#storage_path { font-size: 12px; color: $text_muted; }
QWidget#storage_page QLabel#storage_cell_text { font-size: 14px; }
QWidget#storage_page QLabel#storage_pill { font-size: 12px; font-weight: 700; border: 1px solid $border; border-radius: 12px; padding: 4px 10px; background: $bg_card_alt; color: $text_secondary; }
QWidget#storage_page QLabel#storage_pill[tone="success"] { color: $success; }
QWidget#storage_page QLabel#storage_pill[tone="warning"] { color: $warning; }
QWidget#storage_page QPushButton#storage_reclaim { color: $accent_secondary; }
QWidget#storage_page QPushButton#storage_open, QWidget#storage_page QPushButton#storage_delete { min-height: 44px; padding: 0 12px; border-radius: 12px; }
QWidget#storage_page QPushButton#storage_delete { color: $red_text; border: 1px solid $red_text; }
QPushButton#hero_resume_button { background: $accent; color: $on_red; border: none;
    border-radius: 12px; padding: 0 20px; font-weight: 700; font-size: 13px; min-height: 36px; }
QPushButton#hero_resume_button:hover { background: $accent_hover; color: $on_red; }
QPushButton#hero_resume_button:pressed { background: $accent; color: $on_red; }
QFrame#settings_panel { background: $bg_card; border: 1px solid $border; border-radius: 16px; }
QWidget#settings_content { background: $bg_primary; }
QWidget#settings_row { background: transparent; }
QWidget#settings_page QLabel#settings_heading { font-size: 34px; font-weight: 800; }
QWidget#settings_page QLabel#settings_subtitle { font-size: 14px; color: $text_secondary; }
QWidget#settings_page QLabel#settings_panel_title { font-size: 16px; font-weight: 700; }
QWidget#settings_page QLabel#settings_label { font-size: 14px; font-weight: 600; }
QWidget#settings_page QLabel#settings_hint { font-size: 12px; color: $text_secondary; }
QFrame#settings_divider { background: $border; border: none; }
QWidget#settings_page QPushButton { min-height: 36px; padding: 0 14px; border-radius: 10px; }
QWidget#settings_page QComboBox { min-height: 36px; padding: 0 28px 0 12px; min-width: 120px; font-size: 13px; }
QWidget#settings_segments { background: $bg_card_alt; border: 1px solid $border; border-radius: 12px; }
QWidget#settings_segments QPushButton { background: transparent; border: none; color: $text_secondary; }
QWidget#settings_segments QPushButton:checked { background: $text_primary; color: $bg_primary; }
QWidget#settings_page QListWidget { background: $bg_card_alt; border: 1px solid $border; border-radius: 12px; padding: 4px; }
QWidget#settings_page QListWidget::item { min-height: 36px; padding: 0 10px; }
QComboBox { combobox-popup: 0; }
QComboBox QAbstractItemView { background: $bg_card; color: $text_primary;
    border: 1px solid $border; border-radius: 10px; padding: 4px;
    outline: none; selection-background-color: $accent_secondary; selection-color: $on_indigo; }
QComboBox QAbstractItemView::item { min-height: 36px; padding: 4px 12px;
    border: none; border-radius: 6px; background: $bg_card; color: $text_primary; }
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {
    background: $accent_secondary; color: $on_indigo; }
QComboBox QAbstractItemView::item:disabled { color: $text_muted; }
QMenu { background: $bg_card; color: $text_primary; border: 1px solid $border;
    border-radius: 12px; padding: 6px; }
QMenu::item { min-height: 28px; padding: 8px 14px; border-radius: 6px; color: $text_primary; }
QMenu::item:selected { background: $accent_secondary; color: $on_indigo; }
QMenu::item:disabled { color: $text_muted; }
QMenu::separator { height: 1px; background: $border; margin: 6px 8px; }
QPushButton#close_icon_button { min-width: 0; min-height: 0; padding: 0;
    border: none; border-radius: 18px; background: $bg_card_alt; }
QPushButton#close_icon_button:hover { background: $bg_hover; }
QPushButton#close_icon_button:focus { border: 2px solid $border_focus; }
QDialog#workflow_drawer { background: $bg_card; border: none; }
QWidget#workflow_body, QWidget#workflow_field { background: $bg_card; }
QWidget#workflow_header { background: $bg_card; border-bottom: 1px solid $border; }
QFrame#workflow_footer { background: $bg_card; border-top: 1px solid $border; }
QLabel#workflow_title { font-size: 22px; font-weight: 800; color: $text_primary; }
QLabel#workflow_hint { font-size: 14px; color: $text_secondary; }
QLabel#workflow_field_label { font-size: 13px; font-weight: 600; color: $text_secondary; }
QLabel#workflow_row_title { font-size: 16px; font-weight: 700; color: $text_primary; }
QFrame#workflow_card, QFrame#result_card { background: $bg_card_alt; border: none; border-radius: 16px; }
QFrame#result_card[selected="true"] { border: 2px solid $accent_secondary; }
QLabel#workflow_poster { background: transparent; border: 2px dashed $text_muted; border-radius: 14px; color: $text_secondary; }
QDialog#workflow_drawer QLineEdit, QDialog#workflow_drawer QComboBox { min-height: 44px; background: $bg_primary; border: 1px solid $border; border-radius: 12px; padding: 0 14px; }
QDialog#workflow_drawer QTextEdit { min-height: 96px; background: $bg_primary; border: 1px solid $border; border-radius: 12px; padding: 12px; }
QDialog#workflow_drawer QPushButton { min-height: 44px; padding: 0 16px; border-radius: 12px; }
QDialog#workflow_drawer QPushButton#entry_rating { min-width: 0; min-height: 0; padding: 0; border-radius: 8px; }
QDialog#workflow_drawer QPushButton#close_icon_button { min-width: 0; min-height: 0; padding: 0; border-radius: 18px; }
QLabel#workflow_metric { font-size: 26px; font-weight: 800; }
QLabel#workflow_match { border: 1px solid $border; background: transparent; border-radius: 12px; padding: 4px 10px; color: $success; font-size: 12px; font-weight: 700; }
QLabel#workflow_match[tone="warning"] { color: $warning; }
QLabel#workflow_match[tone="danger"] { color: $danger; }
QFrame#workflow_dropzone { border: 2px dashed $text_muted; border-radius: 16px; background: transparent; }
QLabel#workflow_thumbnail { border-radius: 8px; background: $bg_card_alt; color: $accent_secondary; }
QDialog#workflow_drawer QCheckBox, QDialog#workflow_drawer QRadioButton { background: transparent; spacing: 10px; }
QDialog#workflow_drawer QRadioButton::indicator { width: 18px; height: 18px; border: 1px solid $text_muted; border-radius: 9px; background: $bg_card; }
QDialog#workflow_drawer QRadioButton::indicator:checked { width: 12px; height: 12px; border: 4px solid $accent_secondary; border-radius: 10px; background: $text_primary; }
QDialog#workflow_drawer QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid $text_muted; border-radius: 5px; background: $bg_card; }
QDialog#workflow_drawer QCheckBox::indicator:checked { background: $accent_secondary; border-color: $accent_secondary; }
QFrame#workflow_card QWidget, QFrame#result_card QWidget { background: transparent; }
QFrame#workflow_card QPushButton { background: $bg_card_alt; border: 1px solid $border; }
QWidget#merge_content { background: $bg_primary; }
QFrame#merge_panel { background: $bg_card; border: 1px solid $border; border-radius: 16px; }
QWidget#merge_page QLabel#merge_heading { font-size: 28px; font-weight: 800; }
QWidget#merge_page QLabel#merge_panel_title { font-size: 16px; font-weight: 700; }
QWidget#merge_page QLabel#merge_row_title { font-size: 13px; font-weight: 600; }
QWidget#merge_page QLabel#merge_hint { font-size: 13px; color: $text_secondary; }
QWidget#merge_page QLabel#merge_state { color: $warning; background: $bg_card_alt; border: 1px solid $border; border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: 700; }
QWidget#merge_page QPushButton { min-height: 40px; padding: 0 16px; border-radius: 10px; }
QWidget#merge_page QLineEdit, QWidget#merge_page QComboBox { min-height: 40px; border-radius: 10px; padding: 0 12px; background: $bg_primary; }
QWidget#merge_page QComboBox QLineEdit { min-height: 0; border: none; padding: 0; }
QWidget#merge_page QListWidget#merge_roots { background: transparent; border: none; padding: 0; }
QWidget#merge_page QListWidget::item { min-height: 32px; padding: 0 4px; }
QWidget#merge_page QTableWidget { border: none; background: $bg_card; selection-background-color: $bg_card_alt; selection-color: $text_primary; }
QWidget#merge_page QTableWidget::item { padding: 8px 12px; border: none; border-bottom: 1px solid $border; }
QWidget#merge_page QHeaderView::section { background: $bg_card; border: none; border-bottom: 1px solid $border; padding: 0 12px; font-size: 12px; color: $text_muted; }
QWidget#merge_page QTableWidget::indicator, QWidget#merge_page QCheckBox::indicator, QWidget#merge_page QListWidget::indicator { width: 18px; height: 18px; border: 1px solid $text_muted; border-radius: 4px; background: $bg_card_alt; }
QWidget#merge_page QTableWidget::indicator:checked, QWidget#merge_page QCheckBox::indicator:checked, QWidget#merge_page QListWidget::indicator:checked { background: $accent_secondary; border-color: $accent_secondary; }
QFrame#merge_divider { border: none; background: $border; }
QFrame#workflow_edit_panel { background: $bg_card; border: 1px solid $border; border-radius: 18px; }
QFrame#workflow_edit_panel QWidget#workflow_field { background: transparent; }
QWidget#merge_page QLabel#merge_pill { background: $bg_card_alt; border: 1px solid $border; border-radius: 11px; padding: 3px 9px; color: $success; font-size: 11px; font-weight: 600; }
QWidget#merge_page QLabel#merge_pill[review="true"] { color: $warning; }
QLabel#merge_title { font-size: 14px; font-weight: 700; }
QLabel#merge_path { color: $text_muted; font-size: 11px; }
QWidget#merge_page QWidget#merge_pill_cell, QWidget#merge_page QWidget#merge_title_cell { background: transparent; }
QWidget#merge_page QCheckBox { background: transparent; }
QWidget#merge_page QPushButton:disabled { background: $bg_card_alt; color: $text_muted; border: 1px solid $border; }
QFrame#app_title_bar { background: $bg_secondary; border: none; border-bottom: 1px solid $border_light; }
QLabel#app_caption_title { background: transparent; color: $text_primary; font-size: 14px; font-weight: 600; }
QFrame#update_card QPushButton { min-height: 36px; padding: 0 12px; border-radius: 10px; font-size: 12px; }
QFrame#airing_day { background: $bg_card; border: 1px solid $border; border-radius: 16px; }
QFrame#airing_day[today="true"] { border: 1px solid $accent; background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 $accent_tint,stop:1 $bg_card); }
QFrame#airing_day QLabel { background: transparent; border: none; }
QLabel#airing_date { color: $text_secondary; font-size: 12px; font-weight: 700; }
QFrame#airing_day QLabel#airing_today_badge { color: $on_red; background: $accent; border-radius: 9px; padding: 2px 6px; font-size: 10px; font-weight: 700; }
QFrame#airing_day QLabel#airing_release_dot { background: $accent; border-radius: 3px; }
QPushButton#airing_release, QPushButton#airing_release:hover, QPushButton#airing_release:pressed { background: transparent; border: none; padding: 0; min-height: 0; }
QPushButton#airing_release QLabel#airing_release_title { color: $text_primary; font-size: 14px; font-weight: 600; }
QPushButton#airing_release QLabel#airing_release_time { color: $text_secondary; font-size: 13px; }
QLabel#airing_more { color: $red_text; font-size: 12px; font-weight: 700; }
QLabel#airing_empty { color: $text_muted; font-size: 13px; }
QFrame#quit_choice { background: $bg_card_alt; border: 2px solid transparent; border-radius: 16px; }
QFrame#quit_choice[selected="true"] { border-color: $accent_secondary; }
QFrame#quit_choice QLabel { background: transparent; }
QFrame#quit_choice QLabel#quit_icon { background: $bg_primary; border-radius: 12px; }
QLabel#quit_warning { color: $warning; font-size: 14px; }
QFrame#quit_scrim { background: rgba(0,0,0,0.62); }
QToolTip { background: $bg_card_alt; color: $text_primary; border: 1px solid $border;
           border-radius: 8px; font-size: 13px; padding: 6px 10px; }
""")


def build_qss(theme="dark", scale=1.0):
    palette = COLORS.get(theme, COLORS["dark"])
    stylesheet = get_stylesheet(theme) + _SHELL_QSS.substitute(
        palette, on_indigo="#FFFFFF" if theme == "light" else "#0B0C10",
        chevron=(Path(__file__).parent / "assets" / f"chevron-{theme if theme in COLORS else 'dark'}.svg").as_posix()
    )
    return re.sub(r"(font-size:\s*)(\d+)px",
                  lambda match: f"{match[1]}{round(int(match[2]) * scale)}px", stylesheet)


def get_stylesheet(theme: str = "dark") -> str:
    """Generate the complete stylesheet adhering to the reference mockups."""
    c = COLORS.get(theme, COLORS["dark"])

    return f"""
    /* ===== Global Resets ===== */
    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background-color: {c["bg_primary"]};
    }}

    QDialog {{
        background-color: {c["bg_modal"]};
        border-radius: 16px;
    }}

    QLabel {{ background: transparent; border: none; }}
    QScrollArea, QStackedWidget {{ border: none; }}
    QTabWidget#organizer_tabs::pane {{
        border: none;
        background: {c["bg_primary"]};
    }}
    QTabWidget#organizer_tabs QTabBar {{
        background: {c["bg_primary"]};
        border: none;
    }}
    QTabWidget#organizer_tabs QTabBar::tab {{
        background: {c["bg_primary"]};
        color: {c["text_secondary"]};
        border: none;
        border-bottom: 2px solid {c["border"]};
        padding: 13px 22px;
        min-width: 280px;
        margin-right: 6px;
        font-size: 13px;
        font-weight: 600;
    }}
    QTabWidget#organizer_tabs QTabBar::tab:selected {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border-bottom: 2px solid {c["accent"]};
    }}
    QTabWidget#organizer_tabs QTabBar::tab:hover {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}
    QGroupBox {{ background: {c['bg_card']}; border: 1px solid {c['border']}; border-radius: 12px; margin-top: 18px; padding: 20px 14px 14px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 5px; }}
    QWidget#workflow_panel, QDialog#workflow_dialog {{
        background: {c["bg_modal"]};
    }}
    QFrame#final_panel {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
    }}
    QFrame#final_panel > QWidget {{ background: transparent; }}
    QLabel#eyebrow {{
        color: {c["accent"]};
        font-size: 11px;
        font-weight: 700;
    }}
    QPushButton[chip="true"] {{
        padding: 5px 14px;
        border-radius: 13px;
    }}
    QPushButton[chip="true"]:checked {{
        background: {c["text_primary"]};
        color: {c["bg_primary"]};
        border-color: {c["text_primary"]};
    }}
    /* ===== Scrollbars ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c["scrollbar"]};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["scrollbar_hover"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c["scrollbar"]};
        min-width: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c["scrollbar_hover"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        background: none;
    }}

    /* ===== Input Fields ===== */
    QLineEdit {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 8px 14px;
        font-size: 13px;
        selection-background-color: {c["accent"]};
    }}
    QLineEdit:focus {{
        border: 1px solid {c["border_focus"]};
    }}
    QLineEdit::placeholder {{
        color: {c["text_muted"]};
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 10px;
        font-size: 13px;
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {c["border_focus"]};
    }}

    /* ===== Dropdowns ===== */
    QComboBox {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 6px 14px;
        font-size: 13px;
        min-height: 24px;
    }}
    QComboBox:hover {{
        border-color: {c["border_light"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c["text_secondary"]};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 4px;
        selection-background-color: {c["bg_hover"]};
        selection-color: {c["text_primary"]};
    }}

    /* ===== Buttons ===== */
    QPushButton {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c["bg_hover"]};
        border-color: {c["border_light"]};
    }}
    QPushButton:pressed {{
        background-color: {c["border"]};
    }}

    /* Accent Button */
    QPushButton[accent="true"] {{
        background-color: {c["accent"]};
        color: #ffffff;
        border: none;
        font-weight: 600;
    }}
    QPushButton[accent="true"]:hover {{
        background-color: {c["accent_hover"]};
    }}

    /* Danger Button */
    QPushButton[danger="true"] {{
        background-color: transparent;
        color: {c["danger"]};
        border: 1px solid rgba(239, 68, 68, 0.4);
    }}
    QPushButton[danger="true"]:hover {{
        background-color: {c["danger_bg"]};
        border-color: {c["danger"]};
    }}

    /* Filter Pill Buttons */
    QPushButton[pill="true"], QPushButton[pill="True"] {{
        background-color: {c["bg_card"]};
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 19px;
        padding: 0 18px;
        min-height: 0;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton[pill="true"]:hover, QPushButton[pill="True"]:hover {{
        background-color: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}
    QPushButton[pill="true"][active="true"], QPushButton[pill="True"][active="true"] {{
        background-color: #ffffff;
        color: #111827;
        font-weight: 600;
        border: 1px solid transparent;
        border-radius: 19px;
    }}

    /* ===== Tables ===== */
    QTableWidget, QTableView {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        gridline-color: transparent;
        selection-background-color: {c["bg_hover"]};
        selection-color: {c["text_primary"]};
    }}
    QTableWidget::item {{
        padding: 10px 14px;
        border-bottom: 1px solid {c["border"]};
    }}
    QHeaderView::section {{
        background-color: {c["bg_card"]};
        color: {c["text_muted"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        padding: 10px 14px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ===== Headings & Typography ===== */
    QLabel#heading {{
        font-size: 26px;
        font-weight: 700;
        color: {c["text_primary"]};
    }}
    QLabel#subheading {{
        font-size: 13px;
        color: {c["text_secondary"]};
    }}
    QLabel#section_title {{
        font-size: 16px;
        font-weight: 600;
        color: {c["text_primary"]};
    }}

    /* ===== Status & Offline Pills ===== */
    QLabel#status_online {{
        color: {c["success"]};
        background-color: {c["success_bg"]};
        border-radius: 12px;
        padding: 3px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#status_offline {{
        color: {c["warning"]};
        background-color: {c["warning_bg"]};
        border-radius: 12px;
        padding: 3px 12px;
        font-size: 12px;
        font-weight: 600;
    }}

    /* ===== Custom Cards ===== */
    QFrame#hero_card {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #1a0b22, stop:0.4 #431238, stop:1 #b8235a);
        border-radius: 16px;
    }}

    QFrame#stat_box {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
        padding: 16px;
    }}

    QFrame#capacity_hero {{
        background-color: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
        padding: 24px;
    }}

    /* ===== System Menu ===== */
    QMenu {{
        background-color: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {c["bg_hover"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c["border"]};
        margin: 4px 8px;
    }}
    """


def apply_theme(app: QApplication, theme: str = "dark"):
    """Apply saved appearance preferences without changing library data."""
    from app import preferences as prefs
    from PyQt5.QtGui import QPalette
    from PyQt5.QtCore import QTimer
    from app.ui.components.dropdowns import install_dropdown_style
    install_dropdown_style(app)
    requested = theme
    if theme == "system":
        theme = "light" if prefs.windows_light_theme() else "dark"
    scale = prefs.text_scale()
    contrast = prefs.enabled("high_contrast") or prefs.system_high_contrast()
    app.setProperty("animevaultTheme", theme)
    app.setProperty("animevaultRequestedTheme", requested)
    app.setProperty("animevaultDecorations", prefs.enabled("decorations") and not contrast)
    app.setProperty("animevaultHighContrast", contrast)
    app.setProperty("animevaultScale", scale)
    stylesheet = build_qss(theme, scale)
    if contrast:
        palette = app.style().standardPalette()
        bg = palette.color(QPalette.Window).name()
        fg = palette.color(QPalette.WindowText).name()
        selection = palette.color(QPalette.Highlight).name()
        stylesheet += f"QWidget {{ color: {fg}; }} QFrame#settings_panel, QFrame#storage_panel {{ background: {bg}; border: 2px solid {fg}; }} QPushButton, QComboBox, QLineEdit, QTextEdit, QListWidget {{ border: 2px solid {fg}; }} QPushButton:focus, QComboBox:focus {{ border: 2px solid {selection}; }}"
    from app.ui.theme_scopes import update_theme_scopes
    update_theme_scopes(app, stylesheet, QFont("Segoe UI", round(10 * scale)))
    if not hasattr(app, "_appearance_timer"):
        app._appearance_timer = QTimer(app)
        app._appearance_timer.setInterval(3000)
        def follow_windows():
            requested_theme = app.property("animevaultRequestedTheme")
            expected = "light" if prefs.windows_light_theme() else "dark"
            system_contrast = prefs.enabled("high_contrast") or prefs.system_high_contrast()
            if (requested_theme == "system" and expected != app.property("animevaultTheme")) or system_contrast != app.property("animevaultHighContrast"):
                apply_theme(app, requested_theme)
        app._appearance_timer.timeout.connect(follow_windows)
        app._appearance_timer.start()
    from app.ui.window_chrome import install_title_bar_style
    install_title_bar_style(app)
    for widget in app.topLevelWidgets():
        widget.update()
