from importlib import import_module

from textual.screen import Screen

_MODULES = {
    "ArchiveCreationScreen": "archive_creator",
    "FileNameConflict": "common_file_name_do_what",
    "DeleteFiles": "delete_files",
    "Dismissible": "dismissible",
    "FileSearch": "fd_search",
    "FileInUse": "file_in_use",
    "ModalInput": "input",
    "Keybinds": "keybinds",
    "ScopedKeybinds": "keybinds",
    "PasteDropScreen": "paste_drop",
    "PasteScreen": "paste_screen",
    "ContentSearch": "rg_search",
    "ShellExec": "shell_exec",
    "ThemeChooser": "theme_chooser",
    "TrashScreen": "trash",
    "TerminalTooSmall": "way_too_small",
    "YesOrNo": "yes_or_no",
    "ZDToDirectory": "zd_to_directory",
}


def __getattr__(name: str) -> type[Screen]:
    if name not in _MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    screen = getattr(import_module(f".{_MODULES[name]}", __name__), name)
    globals()[name] = screen
    return screen


__all__ = list(_MODULES)
