from textual import events, on
from textual.css.query import NoMatches
from textual.widgets import Button, OptionList, SelectionList
from textual.widgets.option_list import Option

from rovr.functions.icons import get_icon, get_toggle_button_icon
from rovr.variables.constants import config


class SortOrderPopupOptions(Option):
    def __init__(self, icon: list[str], prompt: str, id: str | None = None) -> None:
        self.label = prompt
        super().__init__(" " + icon[0] + " " + prompt + " ", id=id)


class SortOrderButton(Button):
    def __init__(self) -> None:
        super().__init__(
            get_icon("sorting", "alpha_asc")[0],  # default
            classes="option",
            id="sort_order",
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Change Sort Order"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        await self.open_popup(event)

    async def open_popup(
        self,
        event: events.Click | events.Key | Button.Pressed,
    ) -> None:
        try:
            popup_widget = self.app.query_one(SortOrderPopup)
        except NoMatches:
            popup_widget = SortOrderPopup()
            await self.app.mount(popup_widget)
        if isinstance(event, events.Click):
            popup_widget.styles.offset = (event.screen_x, event.screen_y)
        elif isinstance(event, Button.Pressed):
            popup_widget.styles.offset = (
                self.app.mouse_position.x,
                self.app.mouse_position.y,
            )
        elif isinstance(event, events.Key):
            popup_widget.do_adjust = True
        popup_widget.remove_class("hidden")
        popup_widget.focus()


class SortOrderPopup(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self.do_adjust: bool = False

    def on_mount(self) -> None:
        self.styles.layer = "overlay"
        self.file_list: SelectionList = self.app.query_one("#file_list", SelectionList)
        self.button: Button = self.app.query_one(SortOrderButton)
        self.styles.scrollbar_size_vertical = 0

    @on(events.Show)
    def on_show(self, event: events.Show) -> None:
        order = "desc" if self.file_list.sort_descending else "asc"
        self.set_options([
            SortOrderPopupOptions(
                get_icon("sorting", "alpha_" + order), "N[u]a[/]me", id="name"
            ),
            SortOrderPopupOptions(
                get_icon("sorting", "alpha_alt_" + order),
                "[u]E[/]xtension",
                id="extension",
            ),
            SortOrderPopupOptions(
                get_icon("sorting", "numeric_alt_" + order),
                "[u]N[/]atural",
                id="natural",
            ),
            SortOrderPopupOptions(
                get_icon("sorting", "numeric_" + order), "[u]S[/]ize", id="size"
            ),
            SortOrderPopupOptions(
                get_icon("sorting", "time_" + order), "[u]C[/]reated", id="created"
            ),
            SortOrderPopupOptions(
                get_icon("sorting", "time_alt_" + order),
                "[u]M[/]odified",
                id="modified",
            ),
            SortOrderPopupOptions(
                get_toggle_button_icon(
                    "inner_filled" if self.file_list.sort_descending else "inner"
                ),
                "[u]D[/]escending",
                id="descending",
            ),
        ])
        self.highlighted = self.get_option_index(self.file_list.sort_by)
        if self.do_adjust:
            self.do_adjust = False
            self.styles.offset = (
                (self.app.size.width - 16) // 2,
                (self.app.size.height - 9) // 2,
            )

    @on(events.MouseMove)
    def highlight_follow_mouse(self, event: events.MouseMove) -> None:
        hovered_option: int | None = event.style.meta.get("option")
        if hovered_option is not None and not self._options[hovered_option].disabled:
            self.highlighted = hovered_option

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "descending":
            self.file_list.sort_descending = not self.file_list.sort_descending
        else:
            self.file_list.sort_by = event.option.id
        self.go_hide()
        order = "desc" if self.file_list.sort_descending else "asc"
        match self.file_list.sort_by:
            case "name":
                self.button.label = get_icon("sorting", "alpha_" + order)[0]
            case "extension":
                self.button.label = get_icon("sorting", "alpha_alt_" + order)[0]
            case "natural":
                self.button.label = get_icon("sorting", "numeric_alt_" + order)[0]
            case "size":
                self.button.label = get_icon("sorting", "numeric_" + order)[0]
            case "created":
                self.button.label = get_icon("sorting", "time_" + order)[0]
            case "modified":
                self.button.label = get_icon("sorting", "time_alt_" + order)[0]

    async def on_key(self, event: events.Key) -> None:
        # Close menu on Escape
        match event.key.lower():
            case "escape":
                self.go_hide()
                return
            case "a":
                self.highlighted = self.get_option_index("name")
            case "e":
                self.highlighted = self.get_option_index("extension")
            case "n":
                self.highlighted = self.get_option_index("natural")
            case "s":
                self.highlighted = self.get_option_index("size")
            case "c":
                self.highlighted = self.get_option_index("created")
            case "m":
                self.highlighted = self.get_option_index("modified")
            case "d":
                self.highlighted = self.get_option_index("descending")
            case _:
                return
        event.stop()
        self.action_select()

    @on(events.Blur)
    def on_blur(self, event: events.Blur) -> None:
        self.go_hide()

    def go_hide(self) -> None:
        self.add_class("hidden")
        self.file_list.focus()
