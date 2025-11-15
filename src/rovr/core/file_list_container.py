from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalGroup

from rovr.functions import icons
from rovr.search_container import SearchInput

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
