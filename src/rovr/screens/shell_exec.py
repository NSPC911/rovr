from typing import Literal

from textual import events, work
from textual.widgets import Input

from .input import ModalInput
from .typed import ShellExecReturnType

mode_to_subtitle: dict[str, str] = {
    "background": "Run in background",
    "block": "Block until completion",
    "suspend": "Hide app until completion",
}


class ShellExec(ModalInput):
    def __init__(self) -> None:
        super().__init__(
            border_title="Execute Shell Command", border_subtitle="Run in background"
        )
        self.mode: Literal["background", "block", "suspend"] = "background"

    def on_mount(self) -> None:
        super().on_mount()
        self.horizontal_group.classes = self.mode

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "tab":  # cycle through modes
            event.stop()
            modes = list(mode_to_subtitle.keys())
            current_index = modes.index(self.mode)
            self.mode = modes[(current_index + 1) % len(modes)]  # ty: ignore[invalid-assignment]
            self.horizontal_group.border_subtitle = mode_to_subtitle[self.mode]
            self.horizontal_group.classes = self.mode

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss(None)

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(ShellExecReturnType(command=event.input.value, mode=self.mode))
