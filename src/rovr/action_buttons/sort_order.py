from textual import events
from textual.css.query import NoMatches
from textual.widgets import Button, OptionList
from textual.widgets.option_list import Option

from rovr.components import PopupOptionList
from rovr.functions.icons import get_icon, get_toggle_button_icon
from rovr.functions.utils import check_key, get_shortest_bind
from rovr.state_manager import StateManager
from rovr.variables.constants import config

# Get the shortest keybind for each sort option
name_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["name"])
extension_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["extension"])
natural_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["natural"])
size_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["size"])
created_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["created"])
modified_bind = get_shortest_bind(config["keybinds"]["change_sort_order"]["modified"])
descending_bind = get_shortest_bind(
    config["keybinds"]["change_sort_order"]["descending"]
)


class SortOrderPopupOptions(Option):
    def __init__(
        self,
        bind: str,
        prompt: str,
        is_selected: bool,
        id: str | None = None,
    ) -> None:
        self.label = prompt
        super().__init__(
            f" {get_toggle_button_icon('inner_filled' if is_selected else 'inner')} [d]{bind}[/] {prompt}",
            id=id,
        )


class SortOrderButton(Button):
    def __init__(self) -> None:
        super().__init__(
            get_icon("sorting", "alpha_asc")[0],  # default
            classes="option",
            id="sort_order",
        )

    def update_icon(self) -> None:
        state_manager = self.app.query_one("StateManager")
        order = "desc" if state_manager.sort_descending else "asc"
        match state_manager.sort_by:
            case "name":
                self.label = get_icon("sorting", "alpha_" + order)[0]
            case "extension":
                self.label = get_icon("sorting", "alpha_alt_" + order)[0]
            case "natural":
                self.label = get_icon("sorting", "numeric_alt_" + order)[0]
            case "size":
                self.label = get_icon("sorting", "numeric_" + order)[0]
            case "created":
                self.label = get_icon("sorting", "time_" + order)[0]
            case "modified":
                self.label = get_icon("sorting", "time_alt_" + order)[0]

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Change sort order"
        # Set initial icon based on current sort state
        self.update_icon()

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
        popup_widget.pre_show()
        popup_widget.remove_class("hidden")
        popup_widget.focus()


class SortOrderPopup(PopupOptionList):
    def __init__(self) -> None:
        super().__init__()
        self.do_adjust: bool = False

    def on_mount(
        self, event: events.Mount
    ) -> None:  # ty: ignore[invalid-method-override]
        self.button: SortOrderButton = self.app.query_one(SortOrderButton)
        self.styles.scrollbar_size_vertical = 0
        # calling super()._on_mount is useless, and super().mount()
        # doesnt do anything significant

    def pre_show(self) -> None:
        state_manager: StateManager = self.app.query_one(StateManager)
        self.set_options([
            SortOrderPopupOptions(
                name_bind,
                "Name",
                self.app.file_list.sort_by == "name",
                id="name",
            ),
            SortOrderPopupOptions(
                extension_bind,
                "Extension",
                self.app.file_list.sort_by == "extension",
                id="extension",
            ),
            SortOrderPopupOptions(
                natural_bind,
                "Natural",
                self.app.file_list.sort_by == "natural",
                id="natural",
            ),
            SortOrderPopupOptions(
                size_bind,
                "Size",
                self.app.file_list.sort_by == "size",
                id="size",
            ),
            SortOrderPopupOptions(
                created_bind,
                "Created",
                self.app.file_list.sort_by == "created",
                id="created",
            ),
            SortOrderPopupOptions(
                modified_bind,
                "Modified",
                self.app.file_list.sort_by == "modified",
                id="modified",
            ),
            Option("", id="separator", disabled=True),
            SortOrderPopupOptions(
                descending_bind,
                "Descending",
                self.app.file_list.sort_descending,
                id="descending",
            ),
            Option("", id="separator2", disabled=True),
            SortOrderPopupOptions(
                "",  # No keybind for this option
                "This path only",
                state_manager.custom_sort_enabled,
                id="custom_sort",
            ),
        ])
        # just do a quick width check
        width = 0
        for option in self.options:
            if len(str(option.prompt)) > width:
                width = len(str(option.prompt))
        if self.styles.border_left[0] != "":
            width += 1
        if self.styles.border_right[0] != "":
            width += 1
        width -= 7  # for textual markup fix
        self.width = width
        # for future when more options
        height = (
            self.option_count
            + (1 if self.styles.border_top[0] != "" else 0)
            + (1 if self.styles.border_bottom[0] != "" else 0)
        )
        self.height = height
        self.highlighted = self.get_option_index(self.app.file_list.sort_by)
        if self.do_adjust:
            self.do_adjust = False
            self.styles.offset = (
                (self.app.size.width - width) // 2,
                (self.app.size.height - height) // 2,
            )
        self.get_option("separator")._set_prompt(
            "[$secondary]" + ("-" * self.width) + "[/]"
        )
        self.get_option("separator2")._set_prompt(
            "[$secondary]" + ("-" * self.width) + "[/]"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "descending":
            self.app.file_list.sort_descending = not self.app.file_list.sort_descending
        elif event.option.id == "custom_sort":
            # Toggle custom sort for this folder
            state_manager: StateManager = self.app.query_one(StateManager)
            state_manager.toggle_custom_sort()
            # Refresh file list to apply the change
            self.app.file_list.update_file_list(add_to_session=False)
        else:
            self.app.file_list.sort_by = event.option.id
        self.go_hide()
        self.button.update_icon()

    async def on_key(self, event: events.Key) -> None:
        # no i will not refactor this, or accept PRs to refactor this.
        if check_key(event, config["keybinds"]["change_sort_order"]["name"]):
            self.highlighted = self.get_option_index("name")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["extension"]):
            self.highlighted = self.get_option_index("extension")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["natural"]):
            self.highlighted = self.get_option_index("natural")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["size"]):
            self.highlighted = self.get_option_index("size")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["created"]):
            self.highlighted = self.get_option_index("created")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["modified"]):
            self.highlighted = self.get_option_index("modified")
            event.stop()
            self.action_select()
        elif check_key(event, config["keybinds"]["change_sort_order"]["descending"]):
            self.highlighted = self.get_option_index("descending")
            event.stop()
            self.action_select()
