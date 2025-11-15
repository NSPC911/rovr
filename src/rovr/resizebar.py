from textual import events
from textual.geometry import clamp
from textual.widget import Widget
from textual.widgets import Static


class HorizontalResizeBar(Static):
    DEFAULT_CSS = """
    HorizontalResizeBar {
        width: 1;
        height: 1fr;
        border-left: outer $border-blurred;
        &:hover { border-left: outer $primary-darken-2; }
        &.pressed {   border-left: outer $primary-lighten-1; }
    }
    """

    def __init__(
        self, parent: Widget, id: str | None = None, classes: str | None = None
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.connected_container = parent
        self.min_width = 20
        self.max_width = 100
        self.tooltip = "<── Drag to resize ──>"

    def on_mouse_move(self, event: events.MouseMove) -> None:
        # App.mouse_captured refers to the widget that is currently capturing mouse events.
        if self.app.mouse_captured == self:
            total_delta = event.screen_offset - self.position_on_down
            new_size = self.size_on_down - total_delta
            self.connected_container.styles.width = clamp(
                new_size.width, self.min_width, self.max_width
            )

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.max_width = self.app.screen.size.width - 10
        self.position_on_down = event.screen_offset
        self.size_on_down = self.connected_container.size

        self.add_class("pressed")  # this requires a "pressed" class to exist
        self.capture_mouse()

    def on_mouse_up(self) -> None:
        self.remove_class("pressed")
        self.release_mouse()


class VerticalResizeBar(Static):
    DEFAULT_CSS = """
    VerticalResizeBar {
        height: 1;
        width: 1fr;
        border-top: outer $border-blurred;
        &:hover { border-top: outer $primary-darken-2; }
        &.pressed {   border-top: outer $primary-lighten-1; }
        Tooltip {
            offset: -10 0
        }
    }
    """

    def __init__(
        self, parent: Widget, id: str | None = None, classes: str | None = None
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.connected_container = parent
        self.min_height = 5
        self.max_height = 50
        self.tooltip = "Drag to resize"

    def on_mouse_move(self, event: events.MouseMove) -> None:
        # App.mouse_captured refers to the widget that is currently capturing mouse events.
        if self.app.mouse_captured == self:
            total_delta = event.screen_offset - self.position_on_down
            new_size = self.size_on_down - total_delta
            self.connected_container.styles.height = clamp(
                new_size.height, self.min_height, self.max_height
            )

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.max_height = self.app.screen.size.height - 10
        self.position_on_down = event.screen_offset
        self.size_on_down = self.connected_container.size

        self.add_class("pressed")  # this requires a "pressed" class to exist
        self.capture_mouse()

    def on_mouse_up(self) -> None:
        self.remove_class("pressed")
        self.release_mouse()
