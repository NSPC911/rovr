from typing import ClassVar, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import OptionList

from rovr.classes.textual_options import KeybindOption
from rovr.functions import icons
from rovr.functions.utils import check_key
from rovr.search_container import SearchInput
from rovr.variables.constants import config, schema, vindings


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
        # Generate keybind data programmatically
        keybind_data = []
        primary_keys = []
        keybinds_schema = schema["properties"]["keybinds"]["properties"]
        for action, keys in config["keybinds"].items():
            if action in keybinds_schema:
                display_name = keybinds_schema[action].get("display_name", action)
                if not keys:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    if isinstance(keys, str):
                        keys = [keys]
                    formatted_keys = ", ".join(f"<{key}>" for key in keys)
                    primary_keys.append(keys[0])
                keybind_data.append((formatted_keys, display_name))

        # for plugins
        plugins_schema = schema["properties"]["plugins"]["properties"]
        for key, value in config["plugins"].items():
            if "enabled" in value and "keybinds" in value and key in plugins_schema:
                if not value["keybinds"] or not value["enabled"]:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    formatted_keys = ", ".join(f"<{key}>" for key in value["keybinds"])
                    primary_keys.append(value["keybinds"][0])
                plugins_properties = plugins_schema[key]["properties"]
                display_name = plugins_properties["keybinds"].get("display_name", key)
                keybind_data.append((formatted_keys, display_name))

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
        if check_key(event, config["keybinds"]["focus_search"]):
            event.stop()
            self.input.focus()
        elif check_key(event, config["keybinds"]["show_keybinds"]) or event.key == "escape":
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
