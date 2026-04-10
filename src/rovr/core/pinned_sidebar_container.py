from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalGroup

from rovr.components import SearchInput
from rovr.functions import icons

from .pinned_sidebar import PinnedSidebar


class PinnedSidebarContainer(VerticalGroup):
    def __init__(self) -> None:
        super().__init__(
            id="pinned_sidebar_container",
        )
        self.pinned_sidebar = PinnedSidebar(id="pinned_sidebar")

    def compose(self) -> ComposeResult:
        yield SearchInput(
            placeholder=f"{icons.get_icon('general', 'search')[0]} Search"
        )
        yield self.pinned_sidebar

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            self.pinned_sidebar.focus()
