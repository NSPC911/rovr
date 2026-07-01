import contextlib
from fnmatch import fnmatch
from functools import partial
from shlex import split as shplit
from subprocess import Popen
from typing import ClassVar, Literal

from textual import events, work
from textual.app import App
from textual.binding import BindingType
from textual.css.query import NoMatches
from textual.errors import NoWidget
from textual.reactive import var
from textual.widgets import OptionList

from rovr.classes.config import (
    _RightClickItem,
    _RightClickItemOptionsItem,
    _RovrConfigSettingsOpenersAdditionalpropertiesItem,
)
from rovr.classes.textual_options import RightClickMenuOption
from rovr.classes.type_aliases import DirEntryType
from rovr.components import PopupOptionList
from rovr.functions.path import ifed
from rovr.functions.utils import check_key, expand_command, is_archive, run_command
from rovr.variables.constants import bindings, config


async def get_shell_option(
    app: App,
    option: _RightClickItemOptionsItem | _RightClickItem,
    index: int,
) -> RightClickMenuOption | Literal[False] | None:
    """Provides a shell option based on the action, if it is a built in shell action, otherwise returns None

    Args:
        app: The app, needed to check if option should be disabled
        option: The option to provide
        index: The index of the option, used to create a unique id

    Returns:
        The option widget, False (if the object shouldn't be added) or None (if action isn't a shell action)"""
    if isinstance(option["action"], str):
        return None
    action = option["action"]["run"]
    action_parts = action if isinstance(action, list) else [action]
    disabled = False
    dir_entry: DirEntryType | None = getattr(
        app.file_list.highlighted_option, "dir_entry", None
    )
    if any("${highlighted_file}" in part for part in action_parts):
        disabled = not dir_entry
    if not disabled and any("${selected_files}" in part for part in action_parts):
        disabled = await app.file_list.get_selected_objects() == []
    if "if" in option and ifed(app, option["if"]):
        return False

    return RightClickMenuOption(
        f" {option['label'].strip()} ",
        action=option["action"],
        id=f"shell_{index}",
        disabled=disabled,
    )


def give_me_an_option(
    app: App,
    option: _RightClickItemOptionsItem | _RightClickItem,
) -> RightClickMenuOption | None:
    """Provides an option based on the action, if it is a built in action, otherwise returns None

    Args:
        option: The option to provide
        app: The app, needed to check if option should be disabled

    Returns:
        The option widget, or None if the action is not a built in action
    """
    no_items: bool = (
        app.file_list.highlighted_option and app.file_list.highlighted_option.disabled
    )
    cannot_write: bool = app.file_list.options[0].id == "perm"
    no_clip: bool = len(app.Clipboard.selected) == 0
    PartialOption = partial(
        RightClickMenuOption, f" {option['label'].strip()} ", action=option["action"]
    )
    try:
        assert isinstance(option["action"], str)
    except AssertionError:
        return

    match option["action"]:
        case "rovr:copy" | "rovr:cut" | "rovr:rename" | "rovr:delete":
            return PartialOption(id=option["action"][4:], disabled=no_items)
        case "rovr:paste":
            return PartialOption(id="paste", disabled=no_clip or cannot_write)
        case "rovr:new":
            return PartialOption(id="new", disabled=cannot_write)
        case "rovr:zip":
            return PartialOption(id="zip", disabled=no_items)
        case "rovr:unzip":
            return PartialOption(
                id="unzip",
                disabled=not (
                    hasattr(app.file_list.highlighted_option, "dir_entry")
                    and is_archive(app.file_list.highlighted_option.dir_entry.path)
                ),
            )
        case "system:copy_highlighted" | "system:copy_to_system_clip":
            return PartialOption(id=option["action"][6:], disabled=no_items)
        case "system:copy_current_directory":
            try:
                from os import getcwd

                getcwd()
                return PartialOption(id="copy_current_directory", disabled=False)
            except FileNotFoundError:
                return PartialOption(id="copy_current_directory", disabled=True)


class FileListRightClickMenu(PopupOptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self, classes: str | None = None, id: str | None = None) -> None:
        # Only show unzip option for archive files
        super().__init__(
            id=id,
            classes=classes,
            force_highlight_option_list=True,
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

    async def pre_show(self) -> None:
        options = []
        self.longest_prompt = 0
        for i, option in enumerate(config["settings"]["right_click"]):
            if "options" in option:
                new_option = RightClickMenuOption(
                    f" {option['label'].strip()} ",
                    action=None,
                    id=f"group_{i}",
                    disabled=ifed(self.app, option["if"]) if "if" in option else False,
                )
            elif shell_option := await get_shell_option(self.app, option, i):
                new_option = shell_option
            elif shell_option is False:
                continue
            else:
                new_option = give_me_an_option(self.app, option)
            if new_option is None:
                continue
            options.append(new_option)
            self.longest_prompt = max(self.longest_prompt, len(str(new_option.prompt)))
        for option in options:
            if option.id.startswith("group"):
                if getattr(option.prompt, "__len__", lambda: 0)() < self.longest_prompt:
                    option._set_prompt(f"{option.prompt:<{self.longest_prompt}} ")
                else:
                    option._set_prompt(f"{option.prompt} ")
        self.set_options(options)
        self.highlighted = None
        for i, option in enumerate(options):
            if not option.disabled:
                self.call_after_refresh(setattr, self, "highlighted", i)
                break

    @work
    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        # Get the highlighted option
        if event.option.id.startswith("group"):
            assert isinstance(event.option, RightClickMenuOption)
            with contextlib.suppress(NoMatches):
                self.app.query_one(OpenersMenu).display = False
            try:
                child_menu = self.app.query_one(FileListRightClickChildMenu)
                child_menu.target_option = event.option
            except NoMatches:
                await self.app.mount(
                    child_menu := FileListRightClickChildMenu(
                        event.option, id="child_menu"
                    )
                )
            try:
                visible_region = self.screen.find_widget(self).visible_region
            except NoWidget:
                return

            # I swear Textual is on something (it is not _on to_ something)
            # for some reason, top_right is considered as bottom right, so i
            # need to manually parse and get the true top right to set the offset
            # but the funny part is that if i initially mount it in app, i
            # dont need to do this. so like idk man, whatever works
            child_menu.offset = visible_region.top_right - (
                0,
                self.size.height
                + (1 if self.styles.border_top else 0)
                + (1 if self.styles.border_bottom else 0),
            )
            await child_menu.pre_show()
            child_menu.display = True
            self.focus()
            self.display = True
        elif event.option.id == "rovr:open":
            assert isinstance(event.option, RightClickMenuOption)
            with contextlib.suppress(NoMatches):
                self.app.query_one(FileListRightClickChildMenu).display = False
            try:
                child_menu = self.app.query_one(OpenersMenu)
            except NoMatches:
                await self.app.mount(
                    child_menu := OpenersMenu(
                        self.app.file_list.highlighted_option.dir_entry.path
                    )
                )
            try:
                visible_region = self.screen.find_widget(self).visible_region
            except NoWidget:
                return

            # same thing as above, textual really is on something
            child_menu.offset = visible_region.top_right - (
                0,
                self.size.height
                + (1 if self.styles.border_top else 0)
                + (1 if self.styles.border_bottom else 0),
            )
            await child_menu.pre_show()
            child_menu.display = True
            self.focus()
            self.display = True
        else:
            try:
                self.app.query_one(FileListRightClickChildMenu).display = False
                self.app.query_one(OpenersMenu).display = False
            except NoMatches:
                pass

    @work
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
            return
        self.app.hide_popups()
        if event.option.id.startswith("copy_") and hasattr(
            self.app.query_one("CopyButton"), f"{event.option.id}"
        ):
            self.call_next(
                getattr(
                    self.app.query_one("CopyButton"),
                    f"{event.option.id}",
                )
            )
        elif hasattr(self.app.file_list, f"action_{event.option.id}"):
            self.call_next(
                getattr(
                    self.app.file_list,
                    f"action_{event.option.id}",
                )
            )
        elif event.option.id.startswith("shell_"):
            command: str | list[str] = await expand_command(
                self.app, event.option.action["run"]
            )
            proc = run_command(
                self.app,
                command,
                event.option.action["run_type"],
                shell=event.option.action["shell"],
            )
            if isinstance(proc, Popen) and event.option.action["run_type"] != "orphan":
                self.app.shell_thread(proc, "Context Menu")

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

    target_option: var[RightClickMenuOption] = var(
        RightClickMenuOption("", action=None)
    )

    def __init__(
        self,
        target_option: RightClickMenuOption,
        classes: str | None = None,
        id: str | None = None,
    ) -> None:
        self.set_reactive(FileListRightClickChildMenu.target_option, target_option)
        super().__init__(
            id=id,
            classes=classes,
        )
        self.display = False

    def watch_target_option(
        self, old: RightClickMenuOption, new: RightClickMenuOption
    ) -> None:
        if old != new:
            self.call_next(self.pre_show)

    async def pre_show(self) -> None:
        options = []
        try:
            target_group = int(self.target_option.id.split("_")[1])
        except IndexError:
            return
        for i, option in enumerate(
            config["settings"]["right_click"][target_group]["options"]
        ):
            if shell_option := await get_shell_option(self.app, option, i):
                options.append(shell_option)
            elif shell_option is False:
                continue
            elif new_option := give_me_an_option(self.app, option):
                options.append(new_option)
        self.set_options(options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_list = self.app.query_one(FileListRightClickMenu)
        self.call_next(
            option_list.on_option_list_option_selected,
            OptionList.OptionSelected(self, event.option, event.option_index),
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
            self.app.query_one(FileListRightClickMenu).focus()


class OpenersMenu(PopupOptionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    file_path: var[str] = var("")
    openers: var[list[_RovrConfigSettingsOpenersAdditionalpropertiesItem]] = var([])

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def compute_openers(
        self,
    ) -> list[_RovrConfigSettingsOpenersAdditionalpropertiesItem]:
        list_openers: list[_RovrConfigSettingsOpenersAdditionalpropertiesItem] = []
        for pattern, openers in config["settings"].get("openers", {}).items():
            if fnmatch(self.file_path, pattern):
                for opener in openers:
                    if ifed(self.app, opener.get("if", {})):
                        continue
                    else:
                        list_openers.append(opener)
        return list_openers

    async def pre_show(self) -> None:
        options = []
        for i, opener in enumerate(self.openers):
            if isinstance(opener, str):
                options.append(
                    RightClickMenuOption(
                        f" {shplit(opener)} ",
                        action={"run": opener, "run_type": "orphan", "shell": True},
                        id=f"opener_{i}",
                    )
                )
        self.set_options(options)
