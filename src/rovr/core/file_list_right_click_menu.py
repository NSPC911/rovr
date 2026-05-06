import asyncio
from functools import partial
from typing import Awaitable, Callable, ClassVar

from textual import events, on, work
from textual.app import App
from textual.binding import BindingType
from textual.css.query import NoMatches
from textual.errors import NoWidget
from textual.reactive import reactive
from textual.widgets.option_list import Option

from rovr.classes.config import (
    _RovrConfigSettingsRightClickItem,
    _RovrConfigSettingsRightClickItemOptionsItem,
)
from rovr.components import PopupOptionList
from rovr.functions.utils import check_key, is_archive
from rovr.variables.constants import (
    bindings,
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
    PartialOption = partial(Option, f" {option['label'].strip()} ")

    match option["action"]:
        case "rovr:copy":
            return PartialOption("copy", disabled=no_items)
        case "rovr:cut":
            return PartialOption("cut", disabled=no_items)
        case "rovr:paste":
            return PartialOption("paste", disabled=no_clip)
        case "rovr:new":
            return PartialOption("new", disabled=cannot_write)
        case "rovr:rename":
            return PartialOption("rename", disabled=no_items)
        case "rovr:delete":
            return PartialOption("delete", disabled=no_items)
        case "rovr:zip":
            return PartialOption("zip", disabled=no_items)
        case "rovr:unzip":
            return PartialOption(
                "unzip",
                disabled=not (
                    hasattr(app.file_list.highlighted_option, "dir_entry")
                    and is_archive(app.file_list.highlighted_option.dir_entry.path)
                ),
            )
        case "system:copy_highlighted":
            return PartialOption("copy_highlighted", disabled=no_items)
        case "system:copy_current_directory":
            return PartialOption("copy_current_directory", disabled=no_items)
        case "system:copy_to_system_clip":
            return PartialOption("copy_to_system_clip", disabled=no_items)


class FileListRightClickMenu(PopupOptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self, classes: str | None = None, id: str | None = None) -> None:
        # Only show unzip option for archive files
        super().__init__(
            id=id,
            classes=classes,
        )
        self.longest_prompt = 0

    def update_location(self, event: events.Click) -> None:
        super().update_location(event)
        if self.highlighted_option is not None and self.highlighted is not None:
            self.call_after_refresh(
                self.post_message,
                OptionList.OptionHighlighted(
                    self, self.highlighted_option, self.highlighted
                ),
            )

    @on(events.Show)
    def on_show(self) -> None:
        options = []
        self.longest_prompt = 0
        for i, option in enumerate(config["settings"]["right_click"]):
            if "options" in option:
                options.append(
                    Option(
                        f" {option['label'].strip()} ",
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
            try:
                visible_region = self.screen.find_widget(self).visible_region
            except NoWidget:
                await self.remove()
                await self.app.mount(FileListRightClickMenu())
                return

            child_menu.offset = visible_region.top_right - (
                0,
                self.size.height
                + (1 if self.styles.border_top else 0)
                + (1 if self.styles.border_bottom else 0),
            )
            child_menu.display = True
            child_menu.on_show()
            self.focus()
        else:
            try:
                child_menu = self.app.query_one(FileListRightClickChildMenu)
                child_menu.display = False
            except NoMatches:
                pass
        self.refresh()

    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        # Handle menu item selection
        if event.option.id.startswith("group"):
            # need to handle the submenu options here soon
            child_menu = self.app.query_one(FileListRightClickChildMenu)
            child_menu.focus()
            if child_menu.highlighted is None:
                child_menu.highlighted = 0
            self.call_after_refresh(self.refresh)
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

    def on_blur(self, event: events.Blur) -> None:  # ty: ignore[invalid-method-override]
        event.prevent_default().stop()
        try:
            child_menu = self.app.query_one(FileListRightClickChildMenu)
            # Only hide if the child menu isn't the one that stole focus and isn't currently displayed
            if self.app.focused is not child_menu:
                self.go_hide()
                child_menu.display = False
        except NoMatches:
            self.go_hide()


class FileListRightClickChildMenu(PopupOptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

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

    @work
    async def on_blur(self, event: events.Blur) -> None:  # ty: ignore[invalid-method-override]
        from asyncio import sleep

        event.prevent_default().stop()
        await sleep(0)
        if not isinstance(self.app.focused, FileListRightClickMenu):
            self.display = False

    def on_key(self, event: events.Key) -> None:
        if check_key(event, config["keybinds"]["up_tree"]):
            event.prevent_default().stop()
            option_list = self.app.query_one(FileListRightClickMenu)
            option_list.focus()
