from os import getcwd
from pathlib import Path
from typing import Literal, Self

from textual import events, work
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Button, OptionList
from textual.widgets.option_list import Option

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.components.popup_option_list import PopupOptionList
from rovr.functions.icons import get_icon
from rovr.functions.path import dump_exc, normalise
from rovr.functions.system_clipboard import (
    ClipboardError,
    ClipboardToolNotFoundError,
    copy_files_to_system_clipboard,
)
from rovr.functions.utils import check_key, get_shortest_bind
from rovr.variables.constants import config

rovr_bind = get_shortest_bind(config["keybinds"]["extra_copy"]["copy_to_rovr"])
path_bind = get_shortest_bind(config["keybinds"]["extra_copy"]["copy_single_path"])
system_bind = get_shortest_bind(config["keybinds"]["extra_copy"]["copy_to_system_clip"])
copy_parent_bind = get_shortest_bind(
    config["keybinds"]["extra_copy"]["copy_parent_path"]
)


class CopyPanelOption(Option):
    def __init__(self, bind: str, prompt: str, id: str, disabled: bool = False) -> None:
        super().__init__(f" [d]{bind}[/] {prompt}", id=id, disabled=disabled)


class CopyButton(Button):
    ALLOW_MAXIMIZE = False

    class AlternatePressed(Message):
        """Event sent when a `Button` is pressed and there is no Button action.

        Can be handled using `on_button_pressed` in a subclass of
        [`Button`][textual.widgets.Button] or in a parent widget in the DOM.
        """

        def __init__(self, button: Button, click_button: Literal[1, 3] = 1) -> None:
            self.button: Button = button
            self.click_button = click_button
            """The button that was pressed."""
            super().__init__()

        @property
        def control(self) -> Button:
            """An alias for [Pressed.button][textual.widgets.Button.Pressed.button].

            This will be the same value as [Pressed.button][textual.widgets.Button.Pressed.button].
            """
            return self.button

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "copy")[0], classes="option", id="copy", *args, **kwargs
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Copy selected files"

    async def _on_click(self, event: events.Click) -> None:
        event.stop()
        if not self.has_class("-active"):
            if event.button == 1:
                self.press()
            else:
                self.alternate_press()

    def alternate_press(self) -> Self:
        if self.disabled or not self.display:
            return self
        # Manage the "active" effect:
        self._start_active_affect()
        # ...and let other components know that we've just been clicked:
        if self.action is None:
            self.post_message(CopyButton.AlternatePressed(self))
        else:
            self.call_later(
                self.app.run_action, self.action, default_namespace=self._parent
            )
        return self

    async def on_copy_button_alternate_pressed(self, event: AlternatePressed) -> None:
        await self.open_popup(event)

    async def open_popup(self, event: AlternatePressed | events.Key) -> None:
        try:
            popup_widget = self.app.query_one(CopyPanelOptions)
        except NoMatches:
            popup_widget = CopyPanelOptions()
            await self.app.mount(popup_widget)
        if isinstance(event, CopyButton.AlternatePressed):
            popup_widget.styles.offset = (
                self.app.mouse_position.x,
                self.app.mouse_position.y,
            )
        elif isinstance(event, events.Key):
            popup_widget.do_adjust = True
        popup_widget.pre_show()
        popup_widget.remove_class("hidden")
        popup_widget.focus()

    @work
    async def on_button_pressed(self) -> None:
        """Copy selected files to the clipboard"""
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if selected_files:
            self.app.query_one("#clipboard").copy_to_clipboard(selected_files)
        else:
            self.notify(
                "No files selected to copy.", title="Copy Files", severity="warning"
            )

    def copy_path(self) -> None:
        if self.disabled:
            return
        highlighted: FileListSelectionWidget | None = (
            self.app.file_list.highlighted_option
        )
        if highlighted is None or not hasattr(highlighted, "dir_entry"):
            self.notify(
                "No item was highlighted.", title="Copy Path", severity="information"
            )
        else:
            self.app.copy_to_clipboard(normalise(highlighted.dir_entry.path))
            self.notify("Copied!", title="Copy Path", severity="information")

    def copy_parent_path(self) -> None:
        parent_path = Path(getcwd()).parent.as_posix()
        self.app.copy_to_clipboard(parent_path)
        self.notify("Copied!", title="Copy Parent Path", severity="information")

    @work
    async def copy_to_system_clip(self) -> None:
        """Copy selected files to the system clipboard."""
        if self.disabled:
            return
        selected_files = await self.app.file_list.get_selected_objects()
        if not selected_files:
            self.notify(
                "No files selected to copy.", title="System Copy", severity="warning"
            )
            return

        output = await copy_files_to_system_clipboard(selected_files)
        if output is True:
            self.notify(
                "Files copied to system clipboard.",
                title="System Copy",
                severity="information",
            )
        elif isinstance(output, ClipboardToolNotFoundError):
            self.notify(
                str(output),
                title="Missing Clipboard Tool",
                severity="error",
            )
            dump_exc(self, output)
        elif isinstance(output, ClipboardError):
            self.notify(
                str(output),
                title="Clipboard Error",
                severity="error",
            )
            dump_exc(self, output)


class CopyPanelOptions(PopupOptionList):
    def __init__(self) -> None:
        super().__init__()
        self.do_adjust: bool = False

    def on_mount(self, event: events.Mount) -> None:  # ty: ignore[invalid-method-override]
        # calling super()._on_mount is useless, and super().mount()
        # doesnt do anything significant, hence ty ignore
        self.button: CopyButton = self.app.query_one(CopyButton)
        self.styles.scrollbar_size_vertical = 0

    def pre_show(self) -> None:
        should_disable = self.app.file_list.options[0].disabled
        self.set_options([
            CopyPanelOption(
                rovr_bind,
                "Copy files to rovr clipboard ",
                "rovr",
                disabled=should_disable,
            ),
            CopyPanelOption(
                path_bind, "Copy single file path ", "path", disabled=should_disable
            ),
            CopyPanelOption(
                copy_parent_bind, "Copy parent directory path ", "parent_path"
            ),
            CopyPanelOption(
                system_bind,
                "Copy to system clipboard ",
                "system",
                disabled=should_disable,
            ),
        ])
        height = (
            self.option_count
            + (1 if self.styles.border_top[0] != "" else 0)
            + (1 if self.styles.border_bottom[0] != "" else 0)
        )
        width = 0
        for option in self.options:
            if len(str(option.prompt)) > width:
                width = len(str(option.prompt))
        if self.styles.border_left[0] != "":
            width += 1
        if self.styles.border_right[0] != "":
            width += 1
        width -= 7  # for textual markup fix
        if self.do_adjust:
            self.do_adjust = False
            self.styles.offset = (
                (self.app.size.width - width) // 2,
                (self.app.size.height - height) // 2,
            )

    def on_key(self, event: events.Key) -> None:
        if check_key(event, config["keybinds"]["extra_copy"]["copy_to_rovr"]):
            self.button.on_button_pressed()
        elif check_key(event, config["keybinds"]["extra_copy"]["copy_single_path"]):
            self.button.copy_path()
        elif check_key(event, config["keybinds"]["extra_copy"]["copy_to_system_clip"]):
            self.button.copy_parent_path()
        elif check_key(event, config["keybinds"]["extra_copy"]["copy_parent_path"]):
            self.button.copy_to_system_clip()
        else:
            return
        event.stop()
        self.go_hide()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "rovr":
            self.button.on_button_pressed()
        elif event.option.id == "path":
            self.button.copy_path()
        elif event.option.id == "parent_path":
            self.button.copy_parent_path()
        elif event.option.id == "system":
            self.button.copy_to_system_clip()
        else:
            return
        self.go_hide()
