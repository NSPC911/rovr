import contextlib
from typing import Self

from textual import events, on
from textual.widgets import OptionList


class PopupOptionList(OptionList):
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
        self.styles.layer = "overlay"
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
            and hovered_option != self.highlighted
        ):
            self.highlighted = hovered_option
        # no choice here, i want something similar to focus on hover
        # so that it feels better rather than a focus instantly followed
        # by a hide (looks bad, which was why #264 pr was made for pins bar)
        self.reset_focus()

    def focus(self, scroll_visible: bool = True) -> Self:
        # might be weird, but this is really necessary
        # for some reason, focus doesnt seem to reset, which results in
        # all the popups looking like they are focused (because the focus
        # reactive is set to True for some reason), so schedule a reset
        # after refresh to make sure that only this popup is focused
        self.app.call_after_refresh(self.reset_focus)
        return super().focus(scroll_visible)

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
