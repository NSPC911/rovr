from typing import Any, ClassVar, Iterable, cast

from textual import events
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import OptionList

from rovr.classes.mixins import CursorNavigationMixin
from rovr.classes.textual_options import KeybindOption
from rovr.classes.type_aliases import KeyBinding, KeyMap, KeysConfig
from rovr.components import SearchInput
from rovr.functions import icons
from rovr.functions.utils import check_key, dismiss
from rovr.variables.constants import bindings, config, schema


class KeybindList(CursorNavigationMixin, OptionList, inherit_bindings=False):
    key_contexts = ("keybind_list", "lists")
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
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
        super().__init__(*self.list_of_options, id="keybinds_data")

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
        # Generate keybind data
        keybind_data: list[tuple[str, str]] = []
        primary_keys: list[str] = []
        sub_dict_data: list[tuple[str, dict[str, list[str] | str]]] = []
        keybinds_schema = schema["properties"]["keybinds"]["properties"]
        # no choice to use Any, else ty screams at me and I want
        # to see zero errors from ty
        config_keybinds = cast(dict[str, Any], config["keybinds"])
        for action, keys in config_keybinds.items():
            if isinstance(keys, dict):
                # it is a sub-dict, for other modals
                sub_dict_data.append((action, keys))
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
        for key, subdict in sub_dict_data:
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
    key_contexts = ("keybinds", "filter_modal")

    def action_exit(self) -> None:
        dismiss(self, None)

    def action_focus_search(self) -> None:
        self.input.focus()

    def action_cursor(self, offset: int) -> None:
        self.query_one(KeybindList).action_cursor(offset)

    def action_cursor_page(self, pages: float) -> None:
        self.query_one(KeybindList).action_cursor_page(pages)

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="keybinds_group"):
            yield SearchInput(
                always_add_disabled=True,
                placeholder=f"{icons.get_icon('general', 'search')[0]} Search keybinds...",
            )
            yield KeybindList()

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
        if getattr(self.app, "keys", ()):
            return
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
            dismiss(self, event=event)
        elif check_key(
            event, cast(dict[str, Any], config_keybinds["filter_modal"])["down"]
        ):
            event.stop()
            event.prevent_default()
            if self.keybinds_list.options:
                self.keybinds_list.action_cursor_down()
        elif check_key(
            event, cast(dict[str, Any], config_keybinds["filter_modal"])["up"]
        ):
            event.stop()
            event.prevent_default()
            if self.keybinds_list.options:
                self.keybinds_list.action_cursor_up()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if isinstance(event.option, KeybindOption):
            if not event.option.is_layer_bind:
                event.stop()
                dismiss(self, event=event)
                self.app.simulate_key(event.option.key_press)
        else:
            raise RuntimeError(
                f"Expected a <KeybindOption> but received <{type(event.option).__name__}>"
            )

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            dismiss(self)


class ScopedKeybindList(KeybindList):
    def __init__(self, keys: KeysConfig) -> None:
        self.keys = keys
        super().__init__()

    def get_keybind_data(self) -> tuple[list[tuple[str, str]], list[str]]:
        keybind_data: list[tuple[str, str]] = []
        primary_keys: list[str] = []
        for context, context_bindings in self.keys.items():
            grouped: dict[tuple[str, str], list[tuple[str, ...]]] = {}
            for sequence, binding in self._walk_bindings(context_bindings):
                action = binding["action"]
                if action == "noop":
                    continue
                description = binding.get("desc") or action
                grouped.setdefault((action, description), []).append(sequence)

            if not grouped:
                continue
            keybind_data.append(("--section--", context.replace("_", " ").title()))
            primary_keys.append("")
            for (_, description), sequences in grouped.items():
                formatted = " ".join(
                    self._format_sequence(sequence) for sequence in sequences
                )
                keybind_data.append((formatted, description))
                primary_keys.append(sequences[0][0])

        if not keybind_data:
            keybind_data.append(("<disabled>", "No keybindings"))
            primary_keys.append("")
        return keybind_data, primary_keys

    @classmethod
    def _walk_bindings(
        cls, bindings: KeyMap, prefix: tuple[str, ...] = ()
    ) -> Iterable[tuple[tuple[str, ...], KeyBinding]]:
        for key, binding in bindings.items():
            if key == "desc" or not isinstance(binding, dict):
                continue
            if "action" in binding:
                yield prefix + (key,), cast(KeyBinding, binding)
            else:
                yield from cls._walk_bindings(cast(KeyMap, binding), prefix + (key,))

    @staticmethod
    def _format_sequence(sequence: tuple[str, ...]) -> str:
        if len(sequence) == 1:
            return f"<{sequence[0]}>"
        return "".join(f"<{key}>" if "+" in key else key for key in sequence)


class ScopedKeybinds(Keybinds):
    def compose(self) -> ComposeResult:
        with VerticalGroup(id="keybinds_group"):
            yield SearchInput(
                always_add_disabled=True,
                placeholder=f"{icons.get_icon('general', 'search')[0]} Search keybinds...",
            )
            yield ScopedKeybindList(cast(Any, self.app).keys)

    def on_mount(self) -> None:
        self.input = self.query_one(SearchInput)
        self.container = cast(VerticalGroup, self.query_one("#keybinds_group"))
        self.keybinds_list = self.query_one(ScopedKeybindList)
        self.input.focus()
        self.container.border_title = "Keybinds"

        exit_keys = [
            key
            for context in ("keybinds", "filter_modal")
            for key, binding in cast(Any, self.app).keys.get(context, {}).items()
            if isinstance(binding, dict) and binding.get("action") == "exit"
        ]
        close_with = " or ".join(exit_keys) if exit_keys else "outside"
        self.container.border_subtitle = f"Press {close_with} to close"

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
