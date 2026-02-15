from typing import Any, ClassVar, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import OptionList

from rovr.classes.textual_options import KeybindOption
from rovr.components import SearchInput
from rovr.functions import icons
from rovr.functions.utils import check_key
from rovr.variables.constants import config, schema, vindings


class KeybindList(OptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        keybind_data, primary_keybind_data = self.get_keybind_data()

        max_key_width = max(len(keys) for keys, _ in keybind_data)

        self.list_of_options = []
        passed_alt_layer = False
        for (keys, description), primary_key in zip(keybind_data, primary_keybind_data):
            if keys == "alternate layers":
                passed_alt_layer = True
            self.list_of_options.append(
                KeybindOption(
                    keys, description, max_key_width, primary_key, passed_alt_layer
                )
            )
        super().__init__(*self.list_of_options, **kwargs)

    # ignore single clicks
    async def _on_click(self, event: events.Click) -> None:
        """
        React to the mouse being clicked on an item.

        Args:
            event: The click event.
        """
        event.prevent_default()
        clicked_option: int | None = event.style.meta.get("option")
        if clicked_option is not None and not self._options[clicked_option].disabled:
            # in future, if anything was changed, you just need to add the lines below
            if (
                self.highlighted == clicked_option
                and event.chain == 2
                and event.button != 3
            ):
                self.action_select()
            else:
                self.highlighted = clicked_option

    def get_keybind_data(self) -> tuple[list[tuple[str, str]], list[str]]:
        # Generate keybind data programmatically
        keybind_data: list[tuple[str, str]] = []
        primary_keys: list[str] = []
        subkeys: list[tuple[str, dict[str, list[str] | str]]] = []
        keybinds_schema = schema["properties"]["keybinds"]["properties"]
        # no choice to use Any, else ty screams at me and I want
        # to see zero errors from ty
        config_keybinds = cast(dict[str, Any], config["keybinds"])
        for action, keys in config_keybinds.items():
            if isinstance(keys, dict):
                # it is a subdict, for other modals
                subkeys.append((action, keys))
                continue
            if action in keybinds_schema:
                display_name = keybinds_schema[action].get("display_name", action)
                if not keys:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    keys_list: list[str] = [keys] if isinstance(keys, str) else keys
                    formatted_keys = " ".join(f"<{key}>" for key in keys_list)
                    primary_keys.append(keys_list[0])
                keybind_data.append((formatted_keys, display_name))

        keybind_data.append(("plugins", "--section--"))
        primary_keys.append("")
        # for plugins
        plugins_schema = schema["properties"]["plugins"]["properties"]
        config_plugins = cast(dict[str, Any], config["plugins"])
        for key, value in config_plugins.items():
            value_dict = cast(dict[str, Any], value)
            if (
                "enabled" in value_dict
                and "keybinds" in value_dict
                and key in plugins_schema
            ):
                if not value_dict["keybinds"] or not value_dict["enabled"]:
                    formatted_keys = "<disabled>"
                    primary_keys.append("")
                else:
                    formatted_keys = " ".join(f"<{k}>" for k in value_dict["keybinds"])
                    primary_keys.append(value_dict["keybinds"][0])
                plugins_properties = plugins_schema[key]["properties"]
                display_name = plugins_properties["keybinds"].get("display_name", key)
                keybind_data.append((formatted_keys, display_name))

        # for alternate screens
        keybind_data.append(("alternate layers", "--section--"))
        primary_keys.append("")
        for key, subdict in subkeys:
            keybind_data.append(("--section--", key))
            primary_keys.append("")
            keybinds_schema = schema["properties"]["keybinds"]["properties"][key][
                "properties"
            ]
            for action, keys in subdict.items():
                if action in keybinds_schema:
                    display_name = keybinds_schema[action].get("display_name", action)
                    if not keys:
                        formatted_keys = "<disabled>"
                        primary_keys.append("")
                    else:
                        if isinstance(keys, str):
                            keys = [keys]
                        formatted_keys = " ".join(f"<{key}>" for key in keys)
                        primary_keys.append(keys[0])
                    keybind_data.append((formatted_keys, display_name))

        return keybind_data, primary_keys


class Keybinds(ModalScreen):
    def compose(self) -> ComposeResult:
        with VerticalGroup(id="keybinds_group"):
            yield SearchInput(
                always_add_disabled=True,
                placeholder=f"{icons.get_icon('general', 'search')[0]} Search keybinds...",
            )
            yield KeybindList(id="keybinds_data")

    def on_mount(self) -> None:
        self.input: SearchInput = self.query_one(SearchInput)
        self.container = cast(VerticalGroup, self.query_one("#keybinds_group"))
        self.keybinds_list = cast(KeybindList, self.query_one("#keybinds_data"))

        self.input.focus()

        self.container.border_title = "Keybinds"

        config_keybinds = cast(dict[str, Any], config["keybinds"])
        keybind_keys = config_keybinds["show_keybinds"]
        additional_key_string = ""
        if keybind_keys:
            short_key = "?" if keybind_keys[0] == "question_mark" else keybind_keys[0]
            additional_key_string = f"or {short_key} "
        self.container.border_subtitle = f"Press Esc {additional_key_string}to close"

    def on_key(self, event: events.Key) -> None:
        # same thing here, ty will scream at me if not
        config_keybinds = cast(dict[str, Any], config["keybinds"])
        if check_key(event, config_keybinds["focus_search"]):
            event.stop()
            self.input.focus()
        elif check_key(
            event,
            config_keybinds["show_keybinds"]
            + cast(dict[str, Any], config_keybinds["filter_modal"])["exit"],
        ):
            event.stop()
            self.dismiss()
        elif check_key(
            event, cast(dict[str, Any], config_keybinds["filter_modal"])["down"]
        ):
            event.stop()
            if self.keybinds_list.options:
                self.keybinds_list.action_cursor_down()
        elif check_key(
            event, cast(dict[str, Any], config_keybinds["filter_modal"])["up"]
        ):
            event.stop()
            if self.keybinds_list.options:
                self.keybinds_list.action_cursor_up()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if isinstance(event.option, KeybindOption):
            if not event.option.is_layer_bind:
                event.stop()
                self.dismiss()
                self.app.simulate_key(event.option.key_press)
        else:
            raise RuntimeError(
                f"Expected a <KeybindOption> but received <{type(event.option).__name__}>"
            )

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss()
