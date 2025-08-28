from os import path
from typing import ClassVar

from textual import events, on, work
from textual.binding import Binding, BindingType
from textual.geometry import Size
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from rovr import utils
from rovr.exceptions import FolderNotFileError
from rovr.options import PinnedSidebarOption
from rovr.utils import config


class PinnedSidebar(OptionList, inherit_bindings=False):
    # Just so that I can disable space
    BINDINGS: ClassVar[list[BindingType]] = (
        [
            Binding(bind, "cursor_down", "Down", show=False)
            for bind in config["keybinds"]["down"]
        ]
        + [
            Binding(bind, "last", "Last", show=False)
            for bind in config["keybinds"]["end"]
        ]
        + [
            Binding(bind, "select", "Select", show=False)
            for bind in config["keybinds"]["down_tree"]
        ]
        + [
            Binding(bind, "first", "First", show=False)
            for bind in config["keybinds"]["home"]
        ]
        + [
            Binding(bind, "page_down", "Page Down", show=False)
            for bind in config["keybinds"]["page_down"]
        ]
        + [
            Binding(bind, "page_up", "Page Up", show=False)
            for bind in config["keybinds"]["page_up"]
        ]
        + [
            Binding(bind, "cursor_up", "Up", show=False)
            for bind in config["keybinds"]["up"]
        ]
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def _update_lines(self) -> None:
        """Update internal structures when new lines are added."""
        if not self.scrollable_content_region:
            return

        line_cache = self._line_cache
        line_cache.clear()
        padding = self.get_component_styles("option-list--option").padding
        width = self.scrollable_content_region.width - self._get_left_gutter_width()
        for index, option in enumerate(self.options):
            # in future, if anything was changed, you just need to add the line below
            if not option.disabled or option.id.endswith("header"):
                line_cache.index_to_line[index] = len(line_cache.lines)
                line_count = (
                    self._get_visual(option).get_height(
                        self.styles, width - padding.width
                    )
                    + option._divider
                )
                line_cache.heights[index] = line_count
                line_cache.lines.extend([
                    (index, line_no) for line_no in range(0, line_count)
                ])

        last_divider = self.options and self.options[-1]._divider
        virtual_size = Size(
            self.scrollable_content_region.width,
            len(line_cache.lines) - (1 if last_divider else 0),
        )
        if virtual_size != self.virtual_size:
            self.virtual_size = virtual_size
            self._scroll_update(virtual_size)

    @work(exclusive=True)
    async def reload_pins(self) -> None:
        """Reload pins shown

        Raises:
            FolderNotFileError: If the pin location is a file, and not a folder.
        """
        # be extra sure
        available_pins = utils.load_pins()
        pins = available_pins["pins"]
        default = available_pins["default"]
        print(f"Reloading pins: {available_pins}")
        print(f"Reloading default folders: {default}")
        self.clear_options()
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
                icon = utils.get_icon_for_folder(default_folder["name"])
            else:
                icon = utils.get_icon_for_file(default_folder["name"])
            self.add_option(
                PinnedSidebarOption(
                    icon=icon,
                    label=default_folder["name"],
                    id=f"{utils.compress(default_folder['path'])}-default",
                )
            )
        self.add_option(Option(" Pinned", id="pinned-header"))
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
                icon = utils.get_icon_for_folder(pin["name"])
            else:
                icon = utils.get_icon_for_file(pin["name"])
            self.add_option(
                PinnedSidebarOption(
                    icon=icon,
                    label=pin["name"],
                    id=f"{utils.compress(pin['path'])}-pinned",
                )
            )
        self.add_option(Option(" Drives", id="drives-header"))
        drives = utils.get_mounted_drives()
        for drive in drives:
            self.add_option(
                PinnedSidebarOption(
                    icon=utils.get_icon("folder", ":/drive:"),
                    label=drive,
                    id=f"{utils.compress(drive)}-drives",
                )
            )
        self.disable_option("pinned-header")
        self.disable_option("drives-header")

    async def on_mount(self) -> None:
        """Reload the pinned files from the config."""
        self.input: Input = self.parent.query_one(Input)
        self.reload_pins()

    @on(events.Enter)
    @work
    async def show_input_when_hover(self, event: events.Focus) -> None:
        self.input.add_class("show")

    @on(events.Leave)
    @work
    async def hide_input_when_leave(self, event: events.Leave) -> None:
        self.input.remove_class("show")

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
        file_path = utils.decompress(selected_option.id.split("-")[0])
        if not path.isdir(file_path):
            if path.exists(file_path):
                raise FolderNotFileError(
                    f"Expected a folder but got a file: {file_path}"
                )
            else:
                return
        self.app.cd(file_path)
        self.app.query_one("#file_list").focus()
        self.input.clear()

    def on_key(self, event: events.Key) -> None:
        if event.key in config["keybinds"]["focus_search"]:
            self.input.focus()
