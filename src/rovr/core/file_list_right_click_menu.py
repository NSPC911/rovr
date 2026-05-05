import asyncio
from typing import Awaitable, Callable

from textual import events, on, work
from textual.app import App
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets.option_list import Option

from rovr.classes.config import (
    _RovrConfigSettingsRightClickItem,
    _RovrConfigSettingsRightClickItemOptionsItem,
)
from rovr.components import PopupOptionList
from rovr.variables.constants import (
    config,
)
from rovr.widgets import OptionList


def give_me_an_option(
    option: _RovrConfigSettingsRightClickItemOptionsItem
    | _RovrConfigSettingsRightClickItem,
    app: App,
) -> Option | None:
    no_items: bool = (
        app.file_list.highlighted_option and app.file_list.highlighted_option.disabled
    )
    cannot_write: bool = app.file_list.options[0].id == "perm"
    no_clip: bool = len(app.Clipboard.selected) == 0
    match option["action"]:
        case "rovr:copy":
            return Option(f" {option['icon']} Copy ", "copy", disabled=no_items)
        case "rovr:cut":
            return Option(f" {option['icon']} Cut ", "cut", disabled=no_items)
        case "rovr:paste":
            return Option(f" {option['icon']} Paste ", "paste", disabled=no_clip)
        case "rovr:new":
            return Option(f" {option['icon']} New ", "new", disabled=cannot_write)
        case "rovr:rename":
            return Option(f" {option['icon']} Rename ", "rename", disabled=no_items)
        case "rovr:delete":
            return Option(f" {option['icon']} Delete ", "delete", disabled=no_items)
        case "rovr:zip":
            return Option(f" {option['icon']} Zip ", "zip", disabled=no_items)
        case "rovr:unzip":
            return Option(f" {option['icon']} Unzip ", "unzip", disabled=no_items)
        case "system:copy_highlighted":
            return Option(
                f" {option['icon']} Copy Highlighted File Path ",
                "copy_highlighted",
                disabled=no_items,
            )
        case "system:copy_current_directory":
            return Option(
                f" {option['icon']} Copy Current Directory Path ",
                "copy_current_directory",
                disabled=no_items,
            )
        case "system:copy_to_system_clip":
            return Option(
                f" {option['icon']} Copy to OS Clipboard ",
                "copy_to_system_clip",
                disabled=no_items,
            )


class FileListRightClickMenu(PopupOptionList):
    def __init__(self, classes: str | None = None, id: str | None = None) -> None:
        # Only show unzip option for archive files
        super().__init__(
            id=id,
            classes=classes,
        )
        self.longest_prompt = 0

    @on(events.Show)
    def on_show(self) -> None:
        options = []
        self.longest_prompt = 0
        for i, option in enumerate(config["settings"]["right_click"]):
            if "options" in option:
                options.append(
                    Option(
                        f" {option['icon']} {option['group'].capitalize()} ",
                        id=f"group_{i}",
                    )
                )
            else:
                if new_option := give_me_an_option(option, self.app):
                    options.append(new_option)
            self.longest_prompt = max(self.longest_prompt, len(options[-1].prompt))
        for option in options:
            if option.id.startswith("group"):
                if len(option.prompt) < self.longest_prompt - 2:
                    option._set_prompt(f"{option.prompt:<{self.longest_prompt - 2}} ")
                else:
                    option._set_prompt(f"{option.prompt} ")
        self.set_options(options)
        self.call_next(self.refresh)

    @work
    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        # Get the highlighted option
        if event.option.id.startswith("group"):
            try:
                child_menu = self.app.query_one(FileListRightClickChildMenu)
                child_menu.target_option = event.option
            except NoMatches:
                child_menu = FileListRightClickChildMenu(event.option, id="child_menu")
                await self.app.mount(child_menu)
            visible_region = self.screen.find_widget(self).visible_region
            child_menu.offset = visible_region.top_right - (
                0,
                self.size.height
                + (1 if self.styles.border_top else 0)
                + (1 if self.styles.border_bottom else 0),
            )
            child_menu.display = True
            child_menu.on_show()
        else:
            try:
                child_menu = self.app.query_one(FileListRightClickChildMenu)
                child_menu.go_hide()
            except NoMatches:
                pass

    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        # Handle menu item selection
        if event.option.id.startswith("group"):
            # need to handle the submenu options here soon
            return
        elif event.option.id.startswith("copy_") and hasattr(
            self.app.query_one("CopyButton"), f"{event.option.id}"
        ):
            func: Callable[[], Awaitable | None] = getattr(
                self.app.query_one("CopyButton"), f"{event.option.id}"
            )
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
        elif hasattr(self.app.file_list, f"action_{event.option.id}"):
            func: Callable[[], Awaitable | None] = getattr(
                self.app.file_list, f"action_{event.option.id}"
            )
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
        self.app.hide_popups()

    def on_blur(self, event: events.Blur) -> None:
        event.prevent_default().stop()
        try:
            if not self.app.query_one(FileListRightClickChildMenu):
                self.go_hide()
        except NoMatches:
            self.go_hide()


class FileListRightClickChildMenu(PopupOptionList):
    target_option: reactive[Option] = reactive(Option(""))

    def __init__(
        self, target_option: Option, classes: str | None = None, id: str | None = None
    ) -> None:
        self.set_reactive(FileListRightClickChildMenu.target_option, target_option)
        super().__init__(
            id=id,
            classes=classes,
        )
        self.display = False

    def watch_target_option(self, old: Option, new: Option) -> None:
        if old != new:
            self.on_show()

    @on(events.Show)
    def on_show(self) -> None:
        options = []
        try:
            target_group = int(self.target_option.id.split("_")[1])
        except IndexError:
            return
        for option in config["settings"]["right_click"][target_group]["options"]:
            if new_option := give_me_an_option(option, self.app):
                options.append(new_option)
        self.set_options(options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_list = self.app.query_one(FileListRightClickMenu)
        self.call_next(
            option_list.on_option_list_option_selected,
            OptionList.OptionSelected(option_list, event.option, event.option_index),
        )
        self.remove()
