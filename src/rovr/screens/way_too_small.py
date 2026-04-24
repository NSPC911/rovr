import contextlib

from textual import events, work
from textual.app import ComposeResult, ScreenStackError
from textual.containers import Center, HorizontalGroup
from textual.screen import ModalScreen

from rovr.functions.utils import dismiss
from rovr.variables.constants import MaxPossible, ascii_logo
from rovr.widgets import Label, Static


class TerminalTooSmall(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Static(id="filler-up")
        with Center():
            yield Label(ascii_logo, id="logo")
        with Center():
            with HorizontalGroup(id="height"):
                yield Label("Height: ")
                yield Label(f"[$success]{MaxPossible.height}[/] > ")
                yield Label("", id="heightThing")
            with HorizontalGroup(id="width"):
                yield Label("Width : ")
                yield Label(f"[$success]{MaxPossible.width}[/] > ")
                yield Label("", id="widthThing")
        yield Static(id="filler-down")

    def on_mount(self) -> None:
        for child in self.query("*"):
            child.show_horizontal_scrollbar = False
            child.show_vertical_scrollbar = False
        self.extra_changes()

    @work
    async def extra_changes(self) -> None:
        self.query_one("#heightThing", Label).update(
            f"[${'error' if self.size.height < MaxPossible.height else 'success'}]{self.size.height}[/]"
        )
        self.query_one("#widthThing", Label).update(
            f"[${'error' if self.size.width < MaxPossible.width else 'success'}]{self.size.width}[/]"
        )
        for widget in ["#width", "#height", "#filler-up", "#filler-down", "#logo"]:
            self.query_one(widget).classes = "" if self.size.height > 6 else "hidden"

    @work(exclusive=True)
    async def on_resize(self, event: events.Resize) -> None:
        if (
            event.size.height >= MaxPossible.height
            and event.size.width >= MaxPossible.width
        ):
            with contextlib.suppress(ScreenStackError):
                dismiss(self)
            return
        self.extra_changes()

    def on_key(self, event: events.Key) -> None:
        event.stop()

    def on_click(self, event: events.Click) -> None:
        event.stop()
