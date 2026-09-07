from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.widgets import Static

from rovr.components import SearchInput
from rovr.functions import details as detail_utils
from rovr.functions import icons

from .file_list import FileList


class FileListContainer(VerticalGroup):
    def __init__(self) -> None:
        self.filelist = FileList(
            id="file_list",
            name="File List",
            classes="file-list",
        )
        self.details_header = Static(id="file_list_details_header")
        self._remounting = False
        super().__init__(
            id="file_list_container",
        )

    def compose(self) -> ComposeResult:
        yield SearchInput(
            placeholder=f"({icons.get_icon('general', 'search')[0]}) Search something..."
        )
        if detail_utils.get_detail_columns():
            yield self.details_header
        yield self.filelist

    def update_details_header(self) -> None:
        if detail_utils.get_detail_columns():
            self.details_header.update(self.filelist.details_header_text())

    def on_mount(self) -> None:
        self.set_interval(1, self.remount_filelist)

    def on_resize(self) -> None:
        self.filelist.scroll_to_highlight()
        self.update_details_header()

    async def remount_filelist(self) -> None:
        """Replace a detached file list and reconnect its search input."""
        if (
            self._remounting
            or not self.filelist.is_mounted
            or self.filelist.parent is not None
        ):
            return
        self._remounting = True
        search_input = self.query_one(SearchInput)
        search = search_input.value
        try:
            self.filelist = FileList(
                id="file_list",
                name="File List",
                classes="file-list",
            )
            await self.mount(self.filelist)
            await self.filelist.update_file_list(
                add_to_session=False, clear_search=False
            ).wait()
            search_input.items_list = self.filelist
            search_input.value = search
        finally:
            self._remounting = False

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            self.filelist.focus()
