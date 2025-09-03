from textual import events, work
from textual.app import ComposeResult
from textual.containers import Center, HorizontalGroup
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from rovr.variables.constants import MaxPossible, mini_logo

max_possible = MaxPossible()


class TerminalTooSmall(ModalScreen):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Static()
        with Center():
            yield Label(mini_logo)
        with Center():
            with HorizontalGroup(id="height"):
                yield Label("Height: ")
                yield Label(f"[$success]{max_possible.height}[/] > ")
                yield Label("", id="heightThing")
            with HorizontalGroup(id="width"):
                yield Label("Width : ")
                yield Label(f"[$success]{max_possible.width}[/] > ")
                yield Label("", id="widthThing")
        yield Static()

    def on_mount(self) -> None:
        self.query_one("#heightThing", Label).update(
            f"[${'error' if self.size.height < max_possible.height else 'success'}]{self.size.height}[/]"
        )
        self.query_one("#widthThing", Label).update(
            f"[${'error' if self.size.width < max_possible.width else 'success'}]{self.size.width}[/]"
        )

    @work(exclusive=True)
    async def on_resize(self, event: events.Resize) -> None:
        if (
            event.size.height >= max_possible.height
            and event.size.width >= max_possible.width
        ):
            self.dismiss()
            return
        self.query_one("#heightThing", Label).update(
            f"[${'error' if event.size.height < max_possible.height else 'success'}]{event.size.height}[/]"
        )
        self.query_one("#widthThing", Label).update(
            f"[${'error' if event.size.width < max_possible.width else 'success'}]{event.size.width}[/]"
        )

    def on_key(self, event: events.Key) -> None:
        event.stop()
