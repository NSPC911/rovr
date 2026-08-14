from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.geometry import Region
from textual.strip import Strip
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

    def render_lines(self, crop: Region) -> list[Strip]:
        lines = super().render_lines(crop)
        filelist = self.filelist
        if crop.x != 0 or not filelist.select_mode:
            return lines

        checked = filelist.get_visual_style(
            "option-list--option", filelist.CHECKED_COMPONENT_CLASS
        )
        marker_style = Style(bgcolor=checked.foreground.rich_color)
        content_region = filelist.scrollable_content_region

        for output_y, container_y in enumerate(crop.line_range):
            content_y = self.region.y + container_y - content_region.y
            if not 0 <= content_y < content_region.height:
                continue
            try:
                option_index, _ = filelist._lines[filelist.scroll_offset.y + content_y]
                option = filelist.options[option_index]
            except (IndexError, KeyError):
                continue
            if option.value in filelist._selected:
                lines[output_y] = Strip.join((
                    Strip([Segment(" ", marker_style)], 1),
                    lines[output_y].crop(1),
                ))

        return lines

    def update_details_header(self) -> None:
        if detail_utils.get_detail_columns():
            self.details_header.update(self.filelist.details_header_text())

    def on_resize(self, event: events.Resize) -> None:
        self.filelist.scroll_to_highlight()
        self.update_details_header()

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
