from typing import ClassVar, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import OptionList

from rovr.classes.textual_options import KeybindOption
from rovr.functions import icons
from rovr.search_container import SearchInput
from rovr.variables.constants import config, vindings


class KeybindList(OptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        keybind_data, primary_keybind_data = self.get_keybind_data()

        max_key_width = max(len(keys) for keys, _ in keybind_data)

        self.list_of_options = []
        for (keys, description), primary_key in zip(keybind_data, primary_keybind_data):
            self.list_of_options.append(
                KeybindOption(keys, description, max_key_width, primary_key)
            )
        super().__init__(*self.list_of_options, **kwargs)

    def get_keybind_data(self) -> tuple[list[tuple[str, str]], list[str]]:
        # Hardcoded descriptions based on BINDINGS from various files
        keybind_descriptions = {
            # Navigation - from core/file_list.py, core/pinned_sidebar.py
            "up": "Up",
            "down": "Down",
            "home": "First",
            "end": "Last",
            "page_up": "Page Up",
            "page_down": "Page Down",
            "up_tree": "Go up directory",
            "down_tree": "Enter/Select",
            "hist_previous": "History back",
            "hist_next": "History forward",
            # File operations - from core/preview_container.py
            "copy": "Copy",
            "cut": "Cut",
            "paste": "Paste",
            "delete": "Delete",
            "rename": "Rename",
            "new": "New",
            "zip": "Zip",
            "unzip": "Unzip",
            "copy_path": "Copy path",
            # Interface - app-level keybinds
            "focus_file_list": "Focus file list",
            "focus_toggle_pinned_sidebar": "Focus sidebar",
            "focus_toggle_preview_sidebar": "Focus preview",
            "focus_toggle_path_switcher": "Focus path",
            "focus_search": "Search",
            "focus_toggle_processes": "Focus processes",
            "focus_toggle_clipboard": "Focus clipboard",
            "focus_toggle_metadata": "Focus metadata",
            "toggle_pinned_sidebar": "Toggle sidebar",
            "toggle_preview_sidebar": "Toggle preview",
            "toggle_footer": "Toggle footer",
            "toggle_pin": "Pin folder",
            "show_keybinds": "Show keybinds",
            # Selection - from core/preview_container.py
            "toggle_visual": "Visual mode",
            "toggle_all": "Select all",
            "select_up": "Select up",
            "select_down": "Select down",
            "select_page_up": "Select page up",
            "select_page_down": "Select page down",
            "select_home": "Select to top",
            "select_end": "Select to end",
            # Tabs - app-level keybinds
            "tab_new": "New tab",
            "tab_close": "Close tab",
            "tab_next": "Next tab",
            "tab_previous": "Previous tab",
            # Preview - from core/preview_container.py
            "preview_scroll_left": "Scroll left",
            "preview_scroll_right": "Scroll right",
            "preview_select_left": "Select left",
            "preview_select_right": "Select right",
            # Plugins
            "zoxide": "Launch zoxide selector",
            "editor": "Open file with editor",
        }

        # Generate keybind data programmatically
        keybind_data = []
        primary_keys = []
        for action, keys in config["keybinds"].items():
            if action in keybind_descriptions:
                if not keys:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    formatted_keys = ", ".join(f"<{key}>" for key in keys)
                    primary_keys.append(keys[0])
                description = keybind_descriptions[action]
                keybind_data.append((formatted_keys, description))

        # for plugins
        for key, value in config["plugins"].items():
            if (
                "enabled" in value
                and "keybinds" in value
                and key in keybind_descriptions
            ):
                if not value["keybinds"] or not value["enabled"]:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    formatted_keys = ", ".join(f"<{key}>" for key in value["keybinds"])
                    primary_keys.append(value["keybinds"][0])
                description = keybind_descriptions[key]
                keybind_data.append((formatted_keys, description))

        return keybind_data, primary_keys


class Keybinds(ModalScreen):
    def compose(self) -> ComposeResult:
        with VerticalGroup(id="keybinds_group"):
            yield SearchInput(
                always_add_disabled=False,
                placeholder=f"{icons.get_icon('general', 'search')[0]} Search keybinds...",
            )
            yield KeybindList(id="keybinds_data")

    def on_mount(self) -> None:
        self.input = self.query_one(SearchInput)
        self.container = self.query_one("#keybinds_group")
        self.keybinds_list = self.query_one("#keybinds_data")

        # Prevent the first focus to go to search bar
        self.keybinds_list.focus()

        self.container.border_title = "Keybinds"

        keybind_keys = config["keybinds"]["show_keybinds"]
        additional_key_string = ""
        if keybind_keys:
            short_key = "?" if keybind_keys[0] == "question_mark" else keybind_keys[0]
            additional_key_string = f"or {short_key} "
        self.container.border_subtitle = f"Press Esc {additional_key_string}to close"

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case key if key in config["keybinds"]["focus_search"]:
                event.stop()
                self.input.focus()
            case key if key in config["keybinds"]["show_keybinds"] or key == "escape":
                event.stop()
                self.dismiss()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if hasattr(event.option, "key_press"):
            event.stop()
            self.dismiss()
            self.app.simulate_key(cast(KeybindOption, event.option).key_press)
        else:
            raise RuntimeError(
                f"Expected a <KeybindOption> but received <{type(event.option).__name__}>"
            )
