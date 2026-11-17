"""Family-specific layout adapters for the master Library; no data ownership."""
from PyQt5.QtCore import Qt
from app.ui.theme_catalog import is_manga


def configure(page):
    manga=is_manga()
    if getattr(page,'_manga_active',None)==manga:return
    page._manga_active=manga
    from app.ui.components.neumorphic import install
    # Containers paint their own depth: nesting graphics effects suppresses
    # child button shadows on some Qt raster backends.
    install(page.filter_strip,enabled=False);install(page.pagination,enabled=False)
    for control in [page.sort_combo,page.select_multiple_button,*page.pagination.findChildren(__import__('PyQt5.QtWidgets',fromlist=['QPushButton']).QPushButton),*getattr(page,'pill_buttons',{}).values()]:install(control,enabled=manga)
    page.filter_strip.layout().setContentsMargins(12 if manga else 0,10 if manga else 0,12 if manga else 0,10 if manga else 0)
    toggle=page.grid_btn.parentWidget()
    if not hasattr(page,'_sakura_toggle_style'):page._sakura_toggle_style=toggle.styleSheet()
    toggle.setStyleSheet('QFrame{background:white;border:1px solid #c4c9d4;border-radius:10px;}' if manga else page._sakura_toggle_style)
    if manga:
        page._sakura_card_pool=page._card_pool;page._card_pool=getattr(page,'_manga_card_pool',{})
    elif hasattr(page,'_sakura_card_pool'):
        page._manga_card_pool=page._card_pool;page._card_pool=page._sakura_card_pool
    if not hasattr(page,'_sakura_hero'):page._sakura_hero=page.hero_card
    hero=page._sakura_hero
    if manga:
        if not hasattr(page,'_manga_hero'):
            from app.ui.components.manga_hero import MangaHero
            page._manga_hero=MangaHero(page);page._manga_hero.details_clicked.connect(page.card_clicked.emit)
        hero=page._manga_hero
    if page.hero_card is not hero:
        index=page._content_layout.indexOf(page.hero_card);page._content_layout.removeWidget(page.hero_card);page.hero_card.hide();page.hero_card=hero;page._content_layout.insertWidget(max(0,index),hero);hero.show()
    page.pagination.setVisible(manga)
    page.full_calendar_button.setVisible(manga)
    page.heading_label.setText('Vault Archive' if manga else 'All anime')
    page.heading_label.setStyleSheet('font:800 28px "Noto Serif";color:#111217;' if manga else '')
    if manga:
        page.filter_strip.layout().removeWidget(page.sort_controls);page.archive_header_row.addWidget(page.sort_controls)
    else:
        page.archive_header_row.removeWidget(page.sort_controls);page.filter_strip.layout().addWidget(page.sort_controls)
    page._content_layout.setContentsMargins(30 if manga else 20,12,30 if manga else 20,28)
    from PyQt5.QtWidgets import QLabel
    from app.ui.manga_style import section_chip
    for chip in page.findChildren(QLabel,'section_chip'):section_chip(chip,chip.property('sectionGlyph'))
    page.calendar_panel.layout().setContentsMargins(0 if manga else 16,16,0 if manga else 16,16)
    page._airing_week_signature=None;page._grid_signature=None;page._grid_columns=0
    fit_calendar_controls(page)
    if manga and hasattr(page,'_virtual_posters'):
        page._virtual_posters.active=False;page._virtual_posters.timer.stop()
        for card in page._virtual_posters.slots:card.hide()


def fit_calendar_controls(page):
    from PyQt5.QtWidgets import QApplication
    wrapped=is_manga() and ((QApplication.instance().property('animevaultScale') or 1)>1.05 or page.page_scroll.viewport().width()<1050)
    if wrapped==getattr(page,'_calendar_controls_wrapped',False):return
    page._calendar_controls_wrapped=wrapped
    if wrapped:
        page.airing_heading.removeItem(page.calendar_controls);page.calendar_panel.layout().insertLayout(1,page.calendar_controls)
    else:
        page.calendar_panel.layout().removeItem(page.calendar_controls);page.airing_heading.addLayout(page.calendar_controls)
