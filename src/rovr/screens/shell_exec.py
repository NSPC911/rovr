from textual import events, work
from textual.binding import Binding
from textual.widgets import Input

from rovr.functions.utils import dismiss, expand_command

from .input import ModalInput
from .typed import ShellExecReturnType


class ShellExec(ModalInput):
    BINDINGS = [
        Binding("escape", "dismiss"),
        Binding(
            "tab",
            "cycle_mode",
            description="Cycle execution mode",
        ),
        Binding(
            "shift+tab",
            "cycle_mode",
            description="Cycle execution mode",
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            border_title="Execute Shell Command", border_subtitle="Run in background"
        )
        self.orphan: bool = True

    def on_mount(self) -> None:
        super().on_mount()
        self.horizontal_group.add_class(f"orphan--{str(self.orphan).lower()}")

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            dismiss(self, None, event)

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        dismiss(
            self,
            ShellExecReturnType(
                command=await expand_command(self.app, event.input.value),
                orphan=self.orphan,
            ),
            event,
        )

    def action_cycle_mode(self) -> None:
        self.horizontal_group.remove_class(f"orphan--{str(self.orphan).lower()}")
        self.orphan = not self.orphan
        self.horizontal_group.border_subtitle = (
            "Run in background" if self.orphan else "Run in foreground"
        )
        self.horizontal_group.add_class(f"orphan--{str(self.orphan).lower()}")
