from textual import events, on
from textual.widgets import OptionList, SelectionList


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
        super()._on_mount(event)
        self.file_list: SelectionList = self.app.query_one("#file_list", SelectionList)
        self.styles.layer = "overlay"
        self.go_hide()

    def follow_mouse(self, event: events.Click) -> None:
        self.styles.offset = (event.screen_x, event.screen_y)

    @on(events.MouseMove)
    def highlight_follow_mouse(self, event: events.MouseMove) -> None:
        hovered_option: int | None = event.style.meta.get("option")
        if (
            hovered_option is not None
            and 0 <= hovered_option < len(self._options)
            and not self._options[hovered_option].disabled
        ):
            self.highlighted = hovered_option

    @on(events.Blur)
    def on_blur(self, event: events.Blur) -> None:
        self.go_hide()

    def go_hide(self) -> None:
        self.add_class("hidden")
        self.file_list.focus()

    @on(events.Key)
    def check_escape(self, event: events.Key) -> None:
        if event.key == "escape":
            self.go_hide()

    def update_location(self, event: events.Click) -> None:
        self.styles.offset = (event.screen_x, event.screen_y)

    @on(events.Show)
    def force_highlight_option(self, event: events.Show) -> None:
        if self.force_highlight_option_list:
            self.file_list.add_class("-popup-shown")

    @on(events.Hide)
    def unforce_highlight_option(self, event: events.Hide) -> None:
        if self.file_list.has_class("-popup-shown"):
            self.file_list.remove_class("-popup-shown")
