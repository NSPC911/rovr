from os import getcwd

from textual import events, work
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.css.query import NoMatches
from textual.widgets import Static
from textual.widgets._header import HeaderClock

from rovr.variables.constants import config

from .tabs import NewTabButton, Tabline, TablineTab


class HeaderArea(HorizontalGroup):
    tabline = Tabline(TablineTab(directory=getcwd()))

    def compose(self) -> ComposeResult:
        if (
            config["interface"]["clock"]["enabled"]
            and config["interface"]["clock"]["align"] == "left"
        ):
            yield HeaderClock()
        yield self.tabline
        with HorizontalGroup(id="newTabRight"):
            yield NewTabButton()
            yield Static()
        if (
            config["interface"]["clock"]["enabled"]
            and config["interface"]["clock"]["align"] == "right"
        ):
            yield HeaderClock()

    @work(thread=True)
    def on_resize(self, event: events.Resize | None = None) -> None:
        try:
            tab_line = self.query_exactly_one(Tabline)
        except NoMatches:
            return  # havent mounted yet
        # this might be a bit concerning, so im gonna explain it a bit.
        # max width serves to ensure the tab container doesnt get too long
        # and push header clock to the right.
        # width serves to ensure the new tab button follows the tabline's
        # width, so that it always stays at the right
        tab_line.styles.max_width = (
            self.app.size.width
            - (10 if config["interface"]["clock"]["enabled"] else 0)
            - 5
        )
        tab_line_width = 0
        for tab in tab_line.query(TablineTab):
            tab_line_width += len(tab.label.__str__()) + 2
        tab_line.styles.width = tab_line_width
