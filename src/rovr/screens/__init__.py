from importlib import import_module
from typing import TYPE_CHECKING

from textual.screen import Screen

if TYPE_CHECKING:
    from .archive_creator import ArchiveCreationScreen as ArchiveCreationScreen
    from .common_file_name_do_what import FileNameConflict as FileNameConflict
    from .delete_files import DeleteFiles as DeleteFiles
    from .dismissible import Dismissible as Dismissible
    from .fd_search import FileSearch as FileSearch
    from .file_in_use import FileInUse as FileInUse
    from .input import ModalInput as ModalInput
    from .keybinds import Keybinds as Keybinds
    from .keybinds import ScopedKeybinds as ScopedKeybinds
    from .paste_drop import PasteDropScreen as PasteDropScreen
    from .paste_screen import PasteScreen as PasteScreen
    from .rg_search import ContentSearch as ContentSearch
    from .shell_exec import ShellExec as ShellExec
    from .theme_chooser import ThemeChooser as ThemeChooser
    from .trash import TrashScreen as TrashScreen
    from .way_too_small import TerminalTooSmall as TerminalTooSmall
    from .yes_or_no import YesOrNo as YesOrNo
    from .zd_to_directory import ZDToDirectory as ZDToDirectory


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
