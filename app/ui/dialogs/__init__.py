"""Dialog exports are loaded on demand to keep navigation imports acyclic."""
from importlib import import_module

_EXPORTS = {
    "DeleteConfirmDialog": "delete_confirm",
    "CustomEntryDialog": "custom_entry",
    "RematchDialog": "rematch_dialog",
    "WatchedImportDialog": "watched_import_dialog",
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{_EXPORTS[name]}"), name)
    globals()[name] = value
    return value
