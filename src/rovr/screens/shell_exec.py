from typing import Literal

from textual import events, work
from textual.binding import Binding

from rovr.functions.utils import dismiss
from rovr.widgets import Input

from .input import ModalInput
from .typed import ShellExecReturnType

mode_to_subtitle: dict[str, str] = {
    "background": "Run in background",
    "block": "Block until completion",
    "suspend": "Hide app until completion",
}


class ShellExec(ModalInput):
    BINDINGS = [
        Binding("escape", "dismiss"),
        Binding(
            "tab",
            "cycle_mode_forward",
            description="Cycle execution mode forward",
        ),
        Binding(
            "shift+tab",
            "cycle_mode_backward",
            description="Cycle execution mode backward",
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            border_title="Execute Shell Command", border_subtitle="Run in background"
        )
        self.mode: Literal["background", "block", "suspend"] = "background"

    def on_mount(self) -> None:
        super().on_mount()
        self.horizontal_group.classes = self.mode

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            dismiss(self, None)

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        dismiss(self, ShellExecReturnType(command=event.input.value, mode=self.mode))

    def action_cycle_mode_forward(self) -> None:
        modes = list(mode_to_subtitle.keys())
        to_index = modes.index(self.mode) + 1
        self.mode = modes[to_index % len(modes)]  # ty: ignore[invalid-assignment]
        self.horizontal_group.border_subtitle = mode_to_subtitle[self.mode]
        self.horizontal_group.classes = self.mode

    def action_cycle_mode_backward(self) -> None:
        modes = list(mode_to_subtitle.keys())
        to_index = modes.index(self.mode) - 1
        self.mode = modes[to_index % len(modes)]  # ty: ignore[invalid-assignment]
        self.horizontal_group.border_subtitle = mode_to_subtitle[self.mode]
        self.horizontal_group.classes = self.mode
