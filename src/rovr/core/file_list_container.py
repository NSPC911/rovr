from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalGroup

from rovr.components import SearchInput
from rovr.functions import icons

from .file_list import FileList


class FileListContainer(VerticalGroup):
    def __init__(self) -> None:
        self.filelist = FileList(
            id="file_list",
            name="File List",
            classes="file-list",
        )
        super().__init__(
            id="file_list_container",
        )

    def compose(self) -> ComposeResult:
        yield SearchInput(
            placeholder=f"({icons.get_icon('general', 'search')[0]}) Search something..."
        )
        yield self.filelist

    def on_resize(self, event: events.Resize) -> None:
        self.filelist.scroll_to_highlight()

    def remount_filelist(self) -> None:
        """Remount the file list to reset its state"""
        self.filelist.remove()
        self.filelist = FileList(
            id="file_list",
            name="File List",
            classes="file-list",
        )
        self.call_later(self.mount, self.filelist)

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            self.filelist.focus()
