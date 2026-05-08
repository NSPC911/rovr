import contextlib
from typing import Self

from textual import events, on
from textual.dom import NoScreen
from textual.widget import Widget

from rovr.widgets import OptionList


class PopupOptionList(OptionList):
    layer: int = 0

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
        force_highlight_option_list: bool = False,
    ) -> None:
        super().__init__(
            id=id,
            classes=classes,
        )
        self.force_highlight_option_list = force_highlight_option_list

    def _on_mount(self, event: events.Mount) -> None:
        event.prevent_default()
        if self.styles.overflow_y == "scroll":
            self.show_vertical_scrollbar = True
        if self.styles.overflow_x == "scroll":
            self.show_horizontal_scrollbar = True
        self.layer += 1
        self.styles.layer = "overlay_" + str(self.layer)
        self.go_hide()

    def reset_focus(self) -> None:
        for optionlist in self.app.query("PopupOptionList"):
            optionlist.has_focus = False
        self.has_focus = True

    @on(events.MouseMove)
    def highlight_follow_mouse(self, event: events.MouseMove) -> None:
        hovered_option: int | None = event.style.meta.get("option")
        if (
            hovered_option is not None
            and 0 <= hovered_option < len(self._options)
            and not self._options[hovered_option].disabled
        ):
            self.highlighted = hovered_option
        self.reset_focus()

    def focus(self, scroll_visible: bool = True) -> Self:
        def set_focus(widget: Widget) -> None:
            """Callback to set the focus."""
            with contextlib.suppress(NoScreen):
                widget.screen.set_focus(self, scroll_visible=scroll_visible)

        self.refresh()
        self.app.call_later(set_focus, self)
        self.app.call_after_refresh(self.reset_focus)
        return self

    def on_blur(self, event: events.Blur) -> None:
        self.go_hide()

    def go_hide(self) -> None:
        self.display = False
        with contextlib.suppress(Exception):
            # just for the sake of it
            self.app.file_list.focus()

    @on(events.Key)
    def check_escape(self, event: events.Key) -> None:
        if event.key == "escape":
            self.go_hide()

    def update_location(self, event: events.Click) -> None:
        self.styles.offset = (event.screen_x, event.screen_y)

    @on(events.Show)
    def force_highlight_option(self, event: events.Show) -> None:
        if self.force_highlight_option_list:
            self.app.file_list.add_class("-popup-shown")

    @on(events.Hide)
    def stop_force_highlight_option(self, event: events.Hide) -> None:
        if self.app.file_list.has_class("-popup-shown"):
            self.app.file_list.remove_class("-popup-shown")
