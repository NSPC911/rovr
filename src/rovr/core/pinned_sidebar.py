import asyncio
from os import path
from pathlib import Path
from typing import ClassVar

from textual import events, work
from textual.binding import BindingType
from textual.file_monitor import FileMonitor
from textual.types import DuplicateID
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr.classes import FolderNotFileError, PinnedSidebarOption
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.variables.constants import config, vindings
from rovr.variables.maps import VAR_TO_DIR


class PinnedSidebar(OptionList, inherit_bindings=False):
    DRIVE_WATCHER_FREQUENCY: float = config["settings"]["drive_watcher_frequency"]
    # Just so that I can disable space
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        def reload_pins_sync() -> None:
            asyncio.create_task(self.reload_pins())

        self.pin_monitor = FileMonitor(
            [Path(VAR_TO_DIR["CONFIG"]) / "pins.json"], reload_pins_sync
        )

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
        print(f"Reloading pins: {available_pins}")
        print(f"Reloading default folders: {default}")
        for default_folder in default:
            if not path.isdir(default_folder["path"]):
                if path.exists(default_folder["path"]):
                    raise FolderNotFileError(
                        f"Expected a folder but got a file: {default_folder['path']}"
                    )
                else:
                    pass
            if "icon" in default_folder:
                icon = default_folder["icon"]
            elif path.isdir(default_folder["path"]):
                icon = icon_utils.get_icon_for_folder(default_folder["name"])
            else:
                icon = icon_utils.get_icon_for_file(default_folder["name"])
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
            if "icon" in pin:
                icon = pin["icon"]
            elif path.isdir(pin["path"]):
                icon = icon_utils.get_icon_for_folder(pin["name"])
            else:
                icon = icon_utils.get_icon_for_file(pin["name"])
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
        self.clear_options()
        try:
            self.add_options(self.list_of_options)
        except DuplicateID:
            self.app.panic(
                "[bright_blue]pins.json[/] seems to not be properly set up.\n - There definitely are paths that are defined multiple times in it.\n - Can you take a look at it?\nIf you are unsure on how to fix it, you may choose to just [red][i]obliterate[/][/] the file."
            )

    @work
    async def watch_for_drive_changes_and_update(self) -> None:
        self._drives = path_utils.get_mounted_drives()
        while True:
            await asyncio.sleep(self.DRIVE_WATCHER_FREQUENCY)
            try:
                new_drives = path_utils.get_mounted_drives()
                if self._drives != new_drives:
                    self._drives = new_drives
                    self.reload_pins()
            except Exception as e:
                print(
                    f"Exception of type {type(e).__name__} while watching drives: {e}"
                )
                continue

    @work
    async def watch_for_pin_changes(self) -> None:
        while True:
            # for some reason, this value doesn't matter,
            # only the set_interval matters on the delay
            await asyncio.sleep(5)
            self.set_interval(1, self.pin_monitor, name="pin monitor")

    async def on_mount(self) -> None:
        """Reload the pinned files from the config."""
        assert self.parent
        self.input: Input = self.parent.query_one(Input)
        self.watch_for_drive_changes_and_update()
        self.watch_for_pin_changes()
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
