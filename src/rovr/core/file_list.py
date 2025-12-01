import asyncio
import contextlib
from os import getcwd, path
from os import system as cmd
from time import time
from typing import ClassVar

from rich.segment import Segment
from rich.style import Style
from textual import events, on, work
from textual.binding import BindingType
from textual.css.query import NoMatches
from textual.geometry import Region
from textual.strip import Strip
from textual.widgets import Button, Input, OptionList, SelectionList
from textual.widgets.option_list import Option, OptionDoesNotExist
from textual.widgets.selection_list import Selection

from rovr.classes import ArchiveFileListSelection, FileListSelectionWidget
from rovr.classes.session_manager import SessionManager
from rovr.components import PopupOptionList
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.functions import utils
from rovr.variables.constants import buttons_that_depend_on_path, config, vindings


class FileList(SelectionList, inherit_bindings=False):
    """
    OptionList but can multi-select files and folders.
    """

    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(
        self,
        dummy: bool = False,
        enter_into: str = "",
        select: bool = False,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the FileList widget.
        Args:
            dummy (bool): Whether this is a dummy file list.
            enter_into (str): The path to enter into when a folder is selected.
            select (bool): Whether the selection is select or normal.
        """
        super().__init__(*args, **kwargs)
        self.dummy = dummy
        self.enter_into = enter_into
        self.select_mode_enabled = select
        if not self.dummy:
            self.items_in_cwd: set[str] = set()

    def on_mount(self) -> None:
        if not self.dummy and self.parent:
            self.input: Input = self.parent.query_one(Input)

    @property
    def sort_by(self) -> str:
        try:
            return self.app.query_one("StateManager").sort_by
        except (NoMatches, AttributeError):
            return "name"

    @sort_by.setter
    def sort_by(self, value: str) -> None:
        if value not in ["name", "size", "modified", "created", "extension", "natural"]:
            raise ValueError(
                f"Expected sort_by value to be one of 'name', 'size', 'modified', 'created', 'extension' or 'natural', but got '{value}'"
            )
        with contextlib.suppress(NoMatches):
            self.app.query_one("StateManager").sort_by = value

    @property
    def sort_descending(self) -> bool:
        try:
            return self.app.query_one("StateManager").sort_descending
        except (NoMatches, AttributeError):
            return False

    @sort_descending.setter
    def sort_descending(self, value: bool) -> None:
        with contextlib.suppress(NoMatches):
            self.app.query_one("StateManager").sort_descending = value

    @property
    def highlighted_option(self) -> FileListSelectionWidget | None:
        """The currently highlighted option, or `None` if no option is highlighted.

        Returns:
            An Option, or `None`.
        """
        if self.highlighted is not None:
            return self.options[self.highlighted]  # ty: ignore[invalid-argument-type]
        else:
            return None

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
            elif self.select_mode_enabled and event.button != 3:
                self.highlighted = clicked_option
                self.action_select()
            else:
                self.highlighted = clicked_option
        if event.button == 3 and not self.dummy:
            # Show right click menu
            try:
                rightclickoptionlist: FileListRightClickOptionList = self.app.query_one(
                    FileListRightClickOptionList
                )
            except NoMatches:
                # it happens, but I really cannot be bothered to figure it out
                rightclickoptionlist = FileListRightClickOptionList(classes="hidden")
                await self.app.mount(rightclickoptionlist)
            rightclickoptionlist.remove_class("hidden")
            rightclickoptionlist.update_location(event)
            rightclickoptionlist.focus()
            event.stop()

    @work(exclusive=True)
    async def update_file_list(
        self,
        add_to_session: bool = True,
        focus_on: str | None = None,
    ) -> None:
        """Update the file list with the current directory contents.

        Args:
            add_to_session (bool): Whether to add the current directory to the session history.
            focus_on (str | None): A custom item to set the focus as.
        """
        cwd = path_utils.normalise(getcwd())
        # get sessionstate
        try:
            # only happens when the tabs aren't mounted
            session: SessionManager = self.app.tabWidget.active_tab.session
        except AttributeError:
            self.clear_options()
            return
        self.app.file_list_pause_check = True
        try:
            preview = self.app.query_one("PreviewContainer")

            # Separate folders and files
            self.list_of_options: list[FileListSelectionWidget | Selection] = []
            self.items_in_cwd: set[str] = set()

            to_highlight_index: int = 0
            if not focus_on and cwd in session.lastHighlighted:
                last_highlight = session.lastHighlighted[cwd]
                focus_on = last_highlight["name"]
            try:
                folders, files = await path_utils.get_cwd_object(
                    cwd,
                    config["settings"]["show_hidden_files"],
                    sort_by=self.sort_by,  # ty: ignore[invalid-argument-type]
                    reverse=self.sort_descending,
                )
                if not folders and not files:
                    self.list_of_options.append(
                        Selection("   --no-files--", value="", disabled=True)
                    )
                    await preview.remove_children()
                    preview._current_preview_type = "none"
                    preview.border_title = ""
                else:
                    file_list_options = folders + files

                    self.list_of_options = [
                        FileListSelectionWidget(
                            icon=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                        )
                        for item in file_list_options
                    ]
                    items_in_cwd: list[str] = [
                        item["name"] for item in file_list_options
                    ]
                    if focus_on in items_in_cwd:
                        to_highlight_index = items_in_cwd.index(focus_on)
                    self.items_in_cwd = set(items_in_cwd)

            except PermissionError:
                self.list_of_options.append(
                    Selection(
                        " Permission Error: Unable to access this directory.",
                        value="",
                        id="perm",
                        disabled=True,
                    ),
                )
                await preview.remove_children()
                preview._current_preview_type = "none"
                preview.border_title = ""

            # Query buttons once and update disabled state based on file list status
            buttons: list[Button] = [
                self.app.query_one(selector) for selector in buttons_that_depend_on_path
            ]
            should_disable: bool = (
                len(self.list_of_options) == 1 and self.list_of_options[0].disabled
                if self.list_of_options
                else False
            )
            for button in buttons:
                button.disabled = should_disable
            self.app.query_one("#new").disabled = self.list_of_options[0].id == "perm"
            # special check for up tree
            self.app.query_one("#up").disabled = cwd == path.dirname(cwd)

            self.clear_options()
            self.add_options(self.list_of_options)
            # session handler
            self.app.query_one("#path_switcher").value = cwd + (
                "" if cwd.endswith("/") else "/"
            )
            # I question to myself why directories isn't a list[str]
            # but is a list[dict], so I'm down to take some PRs, because
            # I have other things that are more important.
            if add_to_session:
                if session.historyIndex != len(session.directories) - 1:
                    session.directories = session.directories[
                        : session.historyIndex + 1
                    ]
                session.directories.append(cwd)
                if session.lastHighlighted.get(cwd) is None and isinstance(
                    self.list_of_options[0], FileListSelectionWidget
                ):
                    # Hard coding is my passion (referring to the id)
                    session.lastHighlighted[cwd] = {
                        "name": self.list_of_options[0].dir_entry.name,
                        "index": 0,
                    }
                session.historyIndex = len(session.directories) - 1
            elif session.directories == []:
                session.directories = [path_utils.normalise(getcwd())]
            self.app.query_one("Button#back").disabled = session.historyIndex <= 0
            self.app.query_one("Button#forward").disabled = (
                session.historyIndex == len(session.directories) - 1
            )
            if (
                to_highlight_index == 0
                and cwd in session.lastHighlighted
                and session.lastHighlighted[cwd]["index"]
            ):
                to_highlight_index = min(
                    len(self.list_of_options) - 1, session.lastHighlighted[cwd]["index"]
                )
            try:
                self.highlighted = to_highlight_index
            except (OptionDoesNotExist, KeyError):
                self.highlighted = 0
            if self.highlighted_option and isinstance(
                self.highlighted_option, FileListSelectionWidget
            ):
                session.lastHighlighted[cwd] = {
                    "name": self.highlighted_option.dir_entry.name,
                    "index": self.highlighted,
                }

            self.scroll_to_highlight()
            self.app.tabWidget.active_tab.label = (
                path.basename(cwd) if path.basename(cwd) != "" else cwd.strip("/")
            )
            self.app.tabWidget.active_tab.directory = cwd
            self.app.tabWidget.parent.on_resize()
            with self.input.prevent(self.input.Changed):
                self.input.clear()
            if not add_to_session:
                self.input.clear_selected()
            if self.list_of_options[0].disabled:  # special option
                if self.select_mode_enabled:
                    await self.toggle_mode()
                self.update_border_subtitle()
        finally:
            self.app.file_list_pause_check = False

    @work(exclusive=True)
    async def dummy_update_file_list(
        self,
        cwd: str,
    ) -> None:
        """Update the file list with the current directory contents.

        Args:
            cwd (str): The current working directory.
        """
        assert self.parent is not None
        self.enter_into = cwd
        # Separate folders and files
        self.list_of_options = []

        try:
            folders, files = await path_utils.get_cwd_object(
                cwd,
                config["settings"]["show_hidden_files"],
                sort_by=self.sort_by,  # ty: ignore[invalid-argument-type]
                reverse=self.sort_descending,
            )
            if not folders and not files:
                self.list_of_options.append(
                    Selection("  --no-files--", value="", id="", disabled=True)
                )
            else:
                file_list_options = folders + files
                file_list_option_length = len(file_list_options)
                start_time = time()
                for index, item in enumerate(file_list_options):
                    self.list_of_options.append(
                        FileListSelectionWidget(
                            icon=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                        )
                    )
                    if start_time + 0.25 < time():
                        self.parent.border_subtitle = (
                            f"{index + 1} / {file_list_option_length}"
                        )
                        start_time = time()
                    # await so that textual can still be responsive
                    await asyncio.sleep(0)
        except PermissionError:
            self.list_of_options.append(
                Selection(
                    " Permission Error: Unable to access this directory.",
                    id="",
                    value="",
                    disabled=True,
                )
            )
        self.clear_options()
        self.add_options(self.list_of_options)
        self.parent.border_subtitle = ""

    @work(exclusive=True)
    async def create_archive_list(self, file_list: list[str]) -> None:
        """Create a list display for archive file contents.

        Args:
            file_list (list[str]): List of file paths from archive contents.
        """
        assert self.parent is not None
        self.clear_options()
        self.list_of_options = []

        if not file_list:
            self.list_of_options.append(
                Selection("  --no-files--", value="", id="", disabled=True)
            )
        else:
            file_list_length = len(file_list)
            start_time = time()
            for index, file_path in enumerate(file_list):
                if file_path.endswith("/"):
                    icon = icon_utils.get_icon_for_folder(file_path.strip("/"))
                else:
                    icon = icon_utils.get_icon_for_file(file_path)

                # Create a selection widget similar to FileListSelectionWidget but simpler
                # since we don't have dir_entry metadata for archive contents
                self.list_of_options.append(
                    ArchiveFileListSelection(
                        icon,
                        file_path,
                    )
                )
                if start_time + 0.25 < time():
                    self.parent.border_subtitle = f"{index + 1} / {file_list_length}"
                    start_time = time()
                await asyncio.sleep(0)

        self.add_options(self.list_of_options)
        self.parent.border_subtitle = ""

    async def file_selected_handler(self, target_path: str) -> None:
        if self.app._chooser_file:
            self.app.action_quit()
        elif config["plugins"]["editor"]["open_all_in_editor"]:
            if config["plugins"]["editor"]["file_suspend"]:
                with self.app.suspend():
                    cmd(
                        f'{config["plugins"]["editor"]["file_executable"]} "{target_path}"'
                    )
            else:
                self.app.run_in_thread(
                    cmd,
                    f'{config["plugins"]["editor"]["file_executable"]} "{target_path}"',
                )
        else:
            path_utils.open_file(self.app, target_path)

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        # Get the filename from the option id
        event.prevent_default()
        cwd = path_utils.normalise(getcwd())
        # Get the selected option
        selected_option = self.highlighted_option
        if selected_option is None or (
            len(self.options) == 1
            and not hasattr(self.get_option_at_index(0), "dir_entry")
        ):
            return
        file_name = selected_option.dir_entry.name
        self.update_border_subtitle()
        if self.dummy:
            base_path = self.enter_into or cwd
            target_path = path.join(base_path, file_name)
            if path.isdir(target_path):
                # if the folder is selected, then cd there,
                # skipping the middle folder entirely
                self.app.cd(target_path)
                self.app.tabWidget.active_tab.selectedItems = []
                self.app.query_one("#file_list").focus()
            else:
                await self.file_selected_handler(target_path)
                if self.highlighted is None:
                    self.highlighted = 0
                self.app.tabWidget.active_tab.selectedItems = []
        elif not self.select_mode_enabled:
            full_path = path.join(cwd, file_name)
            if path.isdir(full_path):
                self.app.cd(full_path)
            else:
                await self.file_selected_handler(full_path)
            if self.highlighted is None:
                self.highlighted = 0
            self.app.tabWidget.active_tab.selectedItems = []
        else:
            self.app.tabWidget.active_tab.session.selectedItems = self.selected.copy()

    # No clue why I'm using an OptionList method for SelectionList
    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if self.dummy:
            return
        if isinstance(event.option, Selection) and not isinstance(
            event.option, FileListSelectionWidget
        ):
            self.app.query_one("PreviewContainer").remove_children()
            return
        if not isinstance(event.option, FileListSelectionWidget):
            return
        self.update_border_subtitle()
        # Get the highlighted option
        highlighted_option = event.option
        self.app.tabWidget.active_tab.session.lastHighlighted[
            path_utils.normalise(getcwd())
        ] = {"name": highlighted_option.dir_entry.name, "index": self.highlighted}
        # Get the filename from the option id
        # total files as footer
        if self.highlighted is None:
            self.highlighted = 0
        # preview
        self.app.query_one("PreviewContainer").show_preview(
            highlighted_option.dir_entry.path
        )
        self.app.query_one("MetadataContainer").update_metadata(event.option.dir_entry)
        self.app.query_one("#unzip").disabled = not await utils.is_archive(
            highlighted_option.dir_entry.path
        )

    # Use better versions of the checkbox icons
    def _get_left_gutter_width(
        self,
    ) -> int:
        """Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
        # In normal mode or dummy mode, we don't have a gutter
        if self.dummy or not self.select_mode_enabled:
            return 0
        else:
            # Calculate the exact width of the checkbox components
            return len(
                icon_utils.get_toggle_button_icon("left")
                + icon_utils.get_toggle_button_icon("inner")
                + icon_utils.get_toggle_button_icon("right")
                + " "
            )

    def render_line(self, y: int) -> Strip:
        """Render a line in the display.

        Args:
            y: The line to render.

        Returns:
            A [`Strip`][textual.strip.Strip] that is the line to render.
        """
        # Insane monkey patching was done here, mainly:
        # - replacing render_line from OptionList with super_render_line()
        #   to theme selected options when not highlighted.
        # - ignoring rendering of the checkboxes when
        #   it is a dummy or not in select mode.
        #   - ignore checkbox rendering on disabled options.
        # - using custom icons for the checkbox.

        def super_render_line(y: int, selection_style: str = "") -> Strip:
            line_number = self.scroll_offset.y + y
            try:
                option_index, line_offset = self._lines[line_number]
                option = self.options[option_index]
            except IndexError:
                return Strip.blank(
                    self.scrollable_content_region.width,
                    self.get_visual_style("option-list--option").rich_style,
                )

            mouse_over: bool = self._mouse_hovering_over == option_index
            component_class = ""
            if selection_style == "selection-list--button-selected":
                component_class = selection_style
            elif option.disabled:
                component_class = "option-list--option-disabled"
            elif self.highlighted == option_index:
                component_class = "option-list--option-highlighted"
            elif mouse_over:
                component_class = "option-list--option-hover"

            if component_class:
                style = self.get_visual_style("option-list--option", component_class)
            else:
                style = self.get_visual_style("option-list--option")

            strips = self._get_option_render(option, style)
            try:
                strip = strips[line_offset]
            except IndexError:
                return Strip.blank(
                    self.scrollable_content_region.width,
                    self.get_visual_style("option-list--option").rich_style,
                )
            return strip

        # just return standard rendering
        if self.dummy or not self.select_mode_enabled:
            return super_render_line(y)

        # calculate with checkbox rendering
        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return Strip([*super_render_line(y)])

        if selection.disabled:
            return Strip([*super_render_line(y)])

        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        line = super_render_line(y, component_style)
        underlying_style = next(iter(line)).style or self.rich_style
        assert underlying_style is not None

        button_style = self.get_component_rich_style(component_style)

        side_style = Style.from_color(button_style.bgcolor, underlying_style.bgcolor)

        side_style += Style(meta={"option": selection_index})
        button_style += Style(meta={"option": selection_index})

        return Strip([
            Segment(icon_utils.get_toggle_button_icon("left"), style=side_style),
            Segment(
                icon_utils.get_toggle_button_icon("inner_filled")
                if selection.value in self._selected
                else icon_utils.get_toggle_button_icon("inner"),
                style=button_style,
            ),
            Segment(icon_utils.get_toggle_button_icon("right"), style=side_style),
            Segment(" ", style=underlying_style),
            *line,
        ])

    async def toggle_hidden_files(self) -> None:
        """Toggle the visibility of hidden files."""
        config["settings"]["show_hidden_files"] = not config["settings"][
            "show_hidden_files"
        ]
        self.update_file_list(add_to_session=False)
        status = (
            "[$success underline]shown"
            if config["settings"]["show_hidden_files"]
            else "[$error underline]hidden"
        )
        self.app.notify(
            f"Hidden files are now {status}[/]", severity="information", timeout=2.5
        )
        assert self.parent and self.parent.parent
        if self.parent.parent.query("PreviewContainer > FileList") and not self.dummy:
            self.highlighted = self.highlighted

    async def toggle_mode(self) -> None:
        """Toggle the selection mode between select and normal."""
        if (
            self.highlighted_option
            and self.highlighted_option.disabled
            and not self.select_mode_enabled
        ):
            return
        self.select_mode_enabled = not self.select_mode_enabled
        if not self.select_mode_enabled:
            self._line_cache.clear()
            self._option_render_cache.clear()
        self.refresh(layout=True, repaint=True)
        self.app.tabWidget.active_tab.session.selectMode = self.select_mode_enabled
        with self.prevent(SelectionList.SelectedChanged):
            self.deselect_all()
        self.update_border_subtitle()

    async def get_selected_objects(self) -> list[str] | None:
        """Get the selected objects in the file list.
        Returns:
            list[str]: If there are objects at that given location.
            None: If there are no objects at that given location.
        """
        if self.highlighted_option is None or (
            len(self.options) == 1
            and not hasattr(self.get_option_at_index(0), "dir_entry")
        ):
            return
        if not self.select_mode_enabled:
            return [str(path_utils.normalise(self.highlighted_option.dir_entry.path))]
        else:
            values = self.selected
            if not values:
                return []
            options = [self.get_option(value) for value in values]

            return [
                str(path_utils.normalise(option.dir_entry.path))
                for option in options
                if isinstance(option, FileListSelectionWidget)
            ]

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the file list."""
        from rovr.functions.utils import check_key

        if not self.dummy and self.highlighted_option:
            # toggle select mode
            if check_key(event, config["keybinds"]["toggle_visual"]):
                await self.toggle_mode()
            elif check_key(event, config["keybinds"]["toggle_all"]):
                if self.get_option_at_index(0).disabled:
                    return
                if not self.select_mode_enabled:
                    await self.toggle_mode()
                if len(self.selected) == len(self.options):
                    self.deselect_all()
                else:
                    self.select_all()
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_up"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the current and previous file."""
                if self.highlighted == 0:
                    self.select(self.get_option_at_index(0))
                else:
                    self.select(self.highlighted_option)
                    self.action_cursor_up()
                    self.select(self.highlighted_option)
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_down"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the current and next file."""
                if self.highlighted == len(self.options) - 1:
                    self.select(self.get_option_at_index(self.option_count - 1))
                else:
                    self.select(self.highlighted_option)
                    self.action_cursor_down()
                    self.select(self.highlighted_option)
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_page_up"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the options between the current and the previous 'page'."""
                old = self.highlighted
                self.action_page_up()
                new = self.highlighted
                old = 0 if old is None else old
                new = 0 if new is None else new
                assert isinstance(old, int) and isinstance(new, int)
                for index in range(new, old + 1):
                    self.select(self.get_option_at_index(index))
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_page_down"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the options between the current and the next 'page'."""
                old = self.highlighted
                self.action_page_down()
                new = self.highlighted
                old = 0 if old is None else old
                new = 0 if new is None else new
                assert isinstance(old, int) and isinstance(new, int)
                for index in range(old, new + 1):
                    self.select(self.get_option_at_index(index))
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_home"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the options between the current and the first option"""
                old = self.highlighted
                self.action_first()
                new = self.highlighted
                old = 0 if old is None else old
                new = 0 if new is None else new
                assert isinstance(old, int) and isinstance(new, int)
                for index in range(new, old + 1):
                    self.select(self.get_option_at_index(index))
            elif self.select_mode_enabled and check_key(
                event, config["keybinds"]["select_end"]
            ):
                if self.get_option_at_index(0).disabled:
                    return
                """Select the options between the current and the last option"""
                old = self.highlighted
                self.action_last()
                new = self.highlighted
                old = 0 if old is None else old
                new = 0 if new is None else new
                assert isinstance(old, int) and isinstance(new, int)
                for index in range(old, new + 1):
                    self.select(self.get_option_at_index(index))
            elif config["plugins"]["editor"]["enabled"] and check_key(
                event, config["plugins"]["editor"]["keybinds"]
            ):
                if self.highlighted_option and self.highlighted_option.disabled:
                    return
                if path.isdir(self.highlighted_option.dir_entry.path):
                    if config["plugins"]["editor"]["folder_suspend"]:
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["folder_executable"]} "{self.highlighted_option.dir_entry.path}"'
                            )
                    else:
                        self.app.run_in_thread(
                            cmd,
                            f'{config["plugins"]["editor"]["folder_executable"]} "{self.highlighted_option.dir_entry.path}"',
                        )

                else:
                    if config["plugins"]["editor"]["file_suspend"]:
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["file_executable"]} "{self.highlighted_option.dir_entry.path}"'
                            )
                    else:
                        self.app.run_in_thread(
                            cmd,
                            f'{config["plugins"]["editor"]["file_executable"]} "{self.highlighted_option.dir_entry.path}"',
                        )
            # hit buttons with keybinds
            elif not self.select_mode_enabled and check_key(
                event, config["keybinds"]["hist_previous"]
            ):
                if self.app.query_one("#back").disabled:
                    self.app.query_one("UpButton").on_button_pressed(Button.Pressed)
                else:
                    self.app.query_one("BackButton").on_button_pressed(Button.Pressed)
            elif (
                not self.select_mode_enabled
                and check_key(event, config["keybinds"]["hist_next"])
                and not self.app.query_one("#forward").disabled
            ):
                self.app.query_one("ForwardButton").on_button_pressed(Button.Pressed)
            elif not self.select_mode_enabled and check_key(
                event, config["keybinds"]["up_tree"]
            ):
                self.app.query_one("UpButton").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["copy_path"]):
                await self.app.query_one("PathCopyButton").on_button_pressed(
                    Button.Pressed
                )
            # Toggle pin on current directory
            elif check_key(event, config["keybinds"]["toggle_pin"]):
                pin_utils.toggle_pin(path.basename(getcwd()), getcwd())
                await self.app.query_one("PinnedSidebar").reload_pins()
            elif check_key(event, config["keybinds"]["copy"]):
                await self.app.query_one("#copy").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["cut"]):
                await self.app.query_one("#cut").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["paste"]):
                await self.app.query_one("#paste").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["new"]):
                self.app.query_one("#new").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["rename"]):
                self.app.query_one("#rename").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["delete"]):
                await self.app.query_one("#delete").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["zip"]):
                self.app.query_one("#zip").on_button_pressed(Button.Pressed)
            elif check_key(event, config["keybinds"]["unzip"]):
                self.app.query_one("#unzip").on_button_pressed(Button.Pressed)
            # search
            elif check_key(event, config["keybinds"]["focus_search"]):
                self.input.focus()
            # toggle hidden files
            elif check_key(event, config["keybinds"]["toggle_hidden_files"]):
                await self.toggle_hidden_files()

    def update_border_subtitle(self) -> None:
        if self.dummy or type(self.highlighted) is not int or not self.parent:
            return
        elif self.get_option_at_index(0).disabled:
            utils.set_scuffed_subtitle(self.parent, "NORMAL", "0/0")
            # tell metadata to die
            self.app.query_one("MetadataContainer").remove_children()
        elif (not self.select_mode_enabled) or (self.selected is None):
            utils.set_scuffed_subtitle(
                self.parent,
                "NORMAL",
                f"{self.highlighted + 1}/{self.option_count}",
            )
            self.app.tabWidget.active_tab.selectedItems = []
        else:
            utils.set_scuffed_subtitle(
                self.parent, "SELECT", f"{len(self.selected)}/{len(self.options)}"
            )

    def scroll_to_highlight(
        self, top: bool = False, scrolloff: int = config["interface"]["scrolloff"]
    ) -> None:
        """Scroll to the highlighted option.

        Args:
            top: Ensure highlighted option is at the top of the widget.
            scrolloff: Minimum number of lines to keep visible above/below the highlighted option.
                If scrolloff is larger than half the screen height, the cursor will be centered.
        """
        highlighted = self.highlighted
        if type(highlighted) is not int or not self.is_mounted:
            return

        self._update_lines()

        try:
            y = self._index_to_line[highlighted]
        except KeyError:
            return
        height = self._heights[highlighted]

        # --peak-monkey-patching #
        scrollable_height = self.scrollable_content_region.height

        # yazi like
        if scrolloff > scrollable_height / 2:
            super().scroll_to_region(
                Region(0, y, self.scrollable_content_region.width, height),
                force=True,
                animate=False,
                center=True,
                immediate=True,
            )
        else:
            adjusted_y = max(0, y - scrolloff)
            adjusted_height = height + scrolloff * 2

            super().scroll_to_region(
                Region(
                    0, adjusted_y, self.scrollable_content_region.width, adjusted_height
                ),
                force=True,
                animate=False,
                top=top,
                immediate=True,
            )


class FileListRightClickOptionList(PopupOptionList):
    def __init__(self, classes: str | None = None, id: str | None = None) -> None:
        # Only show unzip option for archive files
        super().__init__(
            id=id,
            classes=classes,
        )

    @on(events.Show)
    async def on_show(self, event: events.Show) -> None:
        if hasattr(self, "file_list"):
            file_list = self.file_list
        else:
            file_list = self.app.query_one("#file_list", FileList)
            self.file_list = file_list
        self.set_options([
            Option(f" {icon_utils.get_icon('general', 'copy')[0]} Copy", id="copy"),
            Option(f" {icon_utils.get_icon('general', 'cut')[0]} Cut", id="cut"),
            Option(
                f" {icon_utils.get_icon('general', 'delete')[0]} Delete ", id="delete"
            ),
            Option(
                f" {icon_utils.get_icon('general', 'rename')[0]} Rename ", id="rename"
            ),
            Option(f" {icon_utils.get_icon('general', 'zip')[0]} Zip", id="zip"),
            Option(
                f" {icon_utils.get_icon('general', 'open')[0]} Unzip",
                id="unzip",
                disabled=not await utils.is_archive(
                    file_list.highlighted_option.dir_entry.name
                ),
            ),
        ])
        self.call_next(self.refresh)

    async def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        # Handle menu item selection
        match event.option.id:
            case "copy":
                await self.app.query_one("#copy").on_button_pressed(Button.Pressed)
            case "cut":
                await self.app.query_one("#cut").on_button_pressed(Button.Pressed)
            case "delete":
                await self.app.query_one("#delete").on_button_pressed(Button.Pressed)
            case "rename":
                self.app.query_one("#rename").on_button_pressed(Button.Pressed)
            case "zip":
                self.app.query_one("#zip").on_button_pressed(Button.Pressed)
            case "unzip":
                if not self.app.query_one("#unzip").disabled:
                    self.app.query_one("#unzip").on_button_pressed(Button.Pressed)
            case _:
                return
        self.go_hide()
