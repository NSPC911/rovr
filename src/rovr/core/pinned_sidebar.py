import multiprocessing
from os import R_OK, access, path
from typing import ClassVar, cast

from textual import events, work
from textual.binding import BindingType
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr.classes.exceptions import FolderNotFileError
from rovr.classes.textual_options import PinnedSidebarOption
from rovr.functions import drive_workers as drive_utils
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.variables.constants import bindings, config, os_type


class PinnedSidebar(OptionList, inherit_bindings=False):
    # Just so that I can disable space
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    @work(exclusive=True, thread=True)
    def reload_pins(self) -> None:
        """Reload pins shown

        Raises:
            FolderNotFileError: If the pin location is a file, and not a folder.
        """
        available_pins = cast(
            pin_utils.PinsDict, globals().get("pins", pin_utils.load_pins())
        )
        pins = available_pins["pins"]
        default = available_pins["default"]
        id_list = []
        self.list_of_options = []
        # get current highlight
        prev_highlighted: int = self.highlighted if type(self.highlighted) is int else 0
        self.log(f"Reloading pins: {available_pins}")
        self.log(f"Reloading default folders: {default}")
        for default_folder in default:
            if not isinstance(default_folder["path"], str):
                continue
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
                icon: tuple[str, str] = default_folder["icon"]
            elif path.isdir(default_folder["path"]):
                icon: tuple[str, str] = icon_utils.get_icon_for_folder(
                    default_folder["name"]
                )
            else:
                icon: tuple[str, str] = icon_utils.get_icon_for_file(
                    default_folder["name"]
                )
            if not (
                isinstance(default_folder["path"], str)
                and isinstance(default_folder["name"], str)
            ):
                # just ignore, shouldn't happen
                continue
            new_id = f"{path_utils.compress(default_folder['path'])}-default"
            if new_id not in id_list:
                self.list_of_options.append(
                    PinnedSidebarOption(
                        icon=icon,
                        label=default_folder["name"],
                        id=new_id,
                    )
                )
                id_list.append(new_id)
        self.list_of_options.append(
            Option(" Pinned", id="pinned-header", disabled=True)
        )
        for pin in pins:
            try:
                pin["path"]
            except KeyError:
                continue
            if not isinstance(pin["path"], str):
                continue
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
                # statically analyzed, it is impossible, but because there
                # is no way to tell json it is an immutable list, and type
                # hint is tuple for pin["icon"], this will work in runtime,
                # just wont work when statically analysed.
                icon = pin["icon"]
            elif path.isdir(pin["path"]):
                icon: tuple[str, str] = icon_utils.get_icon_for_folder(pin["name"])
            else:
                icon: tuple[str, str] = icon_utils.get_icon_for_file(pin["name"])
            if not (isinstance(pin["path"], str) and isinstance(pin["name"], str)):
                # just ignore, shouldn't happen
                continue
            new_id = f"{path_utils.compress(pin['path'])}-pinned"
            if new_id not in id_list:
                self.list_of_options.append(
                    PinnedSidebarOption(
                        icon=icon,
                        label=pin["name"],
                        id=new_id,
                    )
                )
                id_list.append(new_id)
        self.list_of_options.append(
            Option(" Drives", id="drives-header", disabled=True)
        )
        self.app.call_from_thread(self.set_options, self.list_of_options)
        if prev_highlighted < len(self.list_of_options):
            self.highlighted = prev_highlighted
            self.refresh_drives(id_list, None)
            return
        self.refresh_drives(id_list, prev_highlighted)

    @work(thread=True)
    def refresh_drives(
        self, id_list: list[str], prev_highlighted: int | None = None
    ) -> None:
        # force refresh
        try:
            result_queue: multiprocessing.Queue[list[str]] = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=drive_utils.get_mounted_drives_worker,
                args=(result_queue, os_type),
            )
            process.start()
            process.join(timeout=2.0)

            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
                if process.is_alive():
                    process.kill()
                return

            if result_queue.empty():
                return

            drives = result_queue.get_nowait()
        except Exception:
            return
        for drive in drives:
            if access(drive, R_OK):
                new_id = f"{path_utils.compress(drive)}-drives"
                if new_id not in id_list:
                    self.list_of_options.append(
                        PinnedSidebarOption(
                            icon=icon_utils.get_icon("folder", ":/drive:"),
                            label=drive,
                            id=new_id,
                        )
                    )
                    id_list.append(new_id)
        self.app.call_from_thread(
            self.add_options,
            self.list_of_options[len(self.list_of_options) - len(drives) :],
        )
        if prev_highlighted is not None and prev_highlighted < len(
            self.list_of_options
        ):
            self.highlighted = prev_highlighted

    def on_mount(self) -> None:
        """Reload the pinned files from the config."""
        assert self.parent
        self.input: Input = self.parent.query_one(Input)
        # peak scheduling
        self.call_later(self.reload_pins)

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
        file_path = path_utils.decompress(selected_option.id.rsplit("-", 1)[0])
        if not path.isdir(file_path):
            if path.exists(file_path):
                raise FolderNotFileError(
                    f"Expected a folder but got a file: {file_path}"
                )
            else:
                return
        self.app.cd(file_path, clear_search=True)
        # do not switch focus for mouse click events
        if not isinstance(event._sender, PinnedSidebar):
            self.app.file_list.focus()
        if self.input.value != "":
            # assume that you don't need to reset the highlighted
            with self.input.prevent(Input.Changed):
                self.input.clear()
                self.set_options(self.list_of_options)
                if event.option.id:
                    self.highlighted = self.get_option_index(event.option.id)

    def on_key(self, event: events.Key) -> None:
        if event.key in config["keybinds"]["focus_search"]:
            self.action_focus_search()

    def action_focus_search(self) -> None:
        self.input.focus()
