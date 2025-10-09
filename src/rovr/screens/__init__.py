from textual.screen import Screen

from .common_file_name_do_what import CommonFileNameDoWhat
from .delete_files import DeleteFiles
from .dismissable import Dismissable
from .file_search import FileSearch
from .give_permission import GiveMePermission
from .input import ModalInput
from .keybinds import Keybinds
from .way_too_small import TerminalTooSmall
from .yes_or_no import YesOrNo
from .zd_to_directory import ZDToDirectory


class DummyScreen(Screen[None]):
    def on_mount(self) -> None:
        self.dismiss()


__all__ = [
    "Dismissable",
    "CommonFileNameDoWhat",
    "DeleteFiles",
    "ModalInput",
    "YesOrNo",
    "ZDToDirectory",
    "FileSearch",
    "GiveMePermission",
    "DummyScreen",
    "TerminalTooSmall",
    "Keybinds",
]
