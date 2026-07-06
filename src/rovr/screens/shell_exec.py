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
        self.in_bg: bool = True

    def on_mount(self) -> None:
        super().on_mount()
        self.horizontal_group.add_class(f"in-bg--{str(self.in_bg).lower()}")

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
                run_type="background" if self.in_bg else "suspend",
            ),
            event,
        )

    def action_cycle_mode(self) -> None:
        self.horizontal_group.remove_class(f"in-bg--{str(self.in_bg).lower()}")
        self.in_bg = not self.in_bg
        self.horizontal_group.border_subtitle = (
            "Run in background" if self.in_bg else "Run in foreground"
        )
        self.horizontal_group.add_class(f"in-bg--{str(self.in_bg).lower()}")
