from os import path
from typing import ClassVar

from textual import events
from textual.binding import BindingType
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr.classes import FolderNotFileError, PinnedSidebarOption
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.variables.constants import config, vindings


class PinnedSidebar(OptionList, inherit_bindings=False):
    # Just so that I can disable space
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def reload_pins(self) -> None:
        """Reload pins shown

        Raises:
            FolderNotFileError: If the pin location is a file, and not a folder.
        """
        # be extra sure
        available_pins = pin_utils.load_pins()
        pins = available_pins["pins"]
        default = available_pins["default"]
        self.list_of_options = []
        # get current highlight
        prev_highlighted: int = self.highlighted if self.highlighted else 0
        self.log(f"Reloading pins: {available_pins}")
        self.log(f"Reloading default folders: {default}")
        for default_folder in default:
            if not path.isdir(default_folder["path"]) and path.exists(
                default_folder["path"]
            ):
                raise FolderNotFileError(
                    f"Expected a folder but got a file: {default_folder['path']}"
                )
            # we already ensured it, so just ignore ty errors
            if (
                "icon" in default_folder
                and isinstance(default_folder["icon"], list)
                and len(default_folder["icon"]) == 2
            ):
                icon: list[str] = default_folder["icon"]
            elif path.isdir(default_folder["path"]):
                icon: list[str] = icon_utils.get_icon_for_folder(default_folder["name"])
            else:
                icon: list[str] = icon_utils.get_icon_for_file(default_folder["name"])
            if not (
                isinstance(default_folder["path"], str)
                and isinstance(default_folder["name"], str)
            ):
                # just ignore, shouldn't happen
                continue
            self.list_of_options.append(
                PinnedSidebarOption(
                    icon=icon,
                    label=default_folder["name"],
                    id=f"{path_utils.compress(default_folder['path'])}-default",
                )
            )
        self.list_of_options.append(
            Option(" Pinned", id="pinned-header", disabled=True)
        )
        for pin in pins:
            try:
                pin["path"]
            except KeyError:
                break
            if not path.isdir(pin["path"]):
                if path.exists(pin["path"]):
                    raise FolderNotFileError(
                        f"Expected a folder but got a file: {pin['path']}"
                    )
                else:
                    pass
            if (
                "icon" in pin
                and isinstance(pin["icon"], list)
                and len(pin["icon"]) == 2
            ):
                icon = pin["icon"]
            elif path.isdir(pin["path"]):
                icon: list[str] = icon_utils.get_icon_for_folder(pin["name"])
            else:
                icon: list[str] = icon_utils.get_icon_for_file(pin["name"])
            if not (isinstance(pin["path"], str) and isinstance(pin["name"], str)):
                # just ignore, shouldn't happen
                continue
            self.list_of_options.append(
                PinnedSidebarOption(
                    icon=icon,
                    label=pin["name"],
                    id=f"{path_utils.compress(pin['path'])}-pinned",
                )
            )
        self.list_of_options.append(
            Option(" Drives", id="drives-header", disabled=True)
        )
        drives = path_utils.get_mounted_drives()
        for drive in drives:
            self.list_of_options.append(
                PinnedSidebarOption(
                    icon=icon_utils.get_icon("folder", ":/drive:"),
                    label=drive,
                    id=f"{path_utils.compress(drive)}-drives",
                )
            )
        self.set_options(self.list_of_options)
        self.highlighted = prev_highlighted

    async def on_mount(self) -> None:
        """Reload the pinned files from the config."""
        assert self.parent
        self.input: Input = self.parent.query_one(Input)
        await self.reload_pins()

    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        """Handle the selection of an option in the pinned sidebar.
        Args:
            event (OptionList.OptionSelected): The event

        Raises:
            FolderNotFileError: If the pin found is a file and not a folder.
        """
        selected_option = event.option
        # Get the file path from the option id
        assert selected_option.id is not None
        file_path = path_utils.decompress(selected_option.id.split("-")[0])
        if not path.isdir(file_path):
            if path.exists(file_path):
                raise FolderNotFileError(
                    f"Expected a folder but got a file: {file_path}"
                )
            else:
                return
        self.app.cd(file_path)
        self.app.query_one("#file_list").focus()
        with self.input.prevent(Input.Changed):
            self.input.clear()

    def on_key(self, event: events.Key) -> None:
        if event.key in config["keybinds"]["focus_search"]:
            self.input.focus()
