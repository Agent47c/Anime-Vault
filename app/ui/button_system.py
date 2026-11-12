"""Shared button geometry and states from the supplied component template."""
from functools import wraps

def rules(root='',c=None,scale=1):
    if c is None:
        from app.ui.home_style import colors
        c=colors()
    p=lambda n:round(n*scale)
    b=(root+' QPushButton').strip()
    return f'''
    {b} {{background:{c['panel']};color:{c['text']};border:1px solid {c['line']};border-radius:{p(9)}px;min-height:{p(36)}px;padding:0 {p(16)}px;font-size:{p(13)}px;font-weight:600;}}
    {b}:hover {{background:{c['raised']};border-color:{c['coral']};}}
    {b}:pressed {{background:{c['raised']};border-color:{c['text']};}}
    {b}:focus {{border:2px solid {c['coral']};}}
    {b}:disabled {{background:{c['raised']};color:{c['muted']};border-color:{c['line']};}}
    {b}[accent='true'], {b}[role='primary'] {{background:{c['coral']};color:{c['on_coral']};border:1px solid {c['coral']};}}
    {b}[accent='true']:hover, {b}[role='primary']:hover {{background:{c['coral']};border-color:{c['text']};}}
    {b}[accent='true']:disabled, {b}[role='primary']:disabled {{background:{c['raised']};color:{c['muted']};border-color:{c['line']};}}
    {b}[buttonSize='large'] {{min-height:{p(44)}px;border-radius:{p(10)}px;padding:0 {p(20)}px;font-size:{p(14)}px;}}
    {b}[buttonSize='extra-large'] {{min-height:{p(52)}px;border-radius:{p(12)}px;padding:0 {p(24)}px;font-size:{p(14)}px;}}
    {b}[role='destructive'] {{color:{c['coral']};border-color:{c['coral']};}}
    {b}[role='folder'] {{background:{c['raised']};color:{c['text']};border:1px solid {c['line']};}}
    '''

def unified(root):
    def decorate(function):
        @wraps(function)
        def styled(*args,**kwargs):
            from PyQt5.QtWidgets import QApplication
            scale=QApplication.instance().property('animevaultScale') or 1
            selector=root(*args,**kwargs) if callable(root) else root
            return function(*args,**kwargs)+rules(selector,scale=scale)
        return styled
    return decorate
