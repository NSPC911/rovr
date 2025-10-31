import asyncio
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
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.functions import utils
from rovr.variables.constants import buttons_that_depend_on_path, config, vindings
from rovr.variables.maps import ARCHIVE_EXTENSIONS_FULL


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
                rightclickoptionlist = FileListRightClickOptionList(
                    self, classes="hidden"
                )
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
            session = self.app.tabWidget.active_tab.session
        except AttributeError:
            self.clear_options()
            return
        # Separate folders and files
        self.list_of_options: list[FileListSelectionWidget | Selection] = []
        names_in_cwd: list[str] = []
        self.items_in_cwd: set[str] = set()
        try:
            folders, files = await path_utils.get_cwd_object(
                cwd, config["settings"]["show_hidden_files"]
            )
            if not folders and not files:
                self.list_of_options.append(
                    Selection("   --no-files--", value="", disabled=True)
                )
                preview = self.app.query_one("PreviewContainer")
                preview.remove_children()
                preview._current_preview_type = "none"
                preview.border_title = ""
            else:
                file_list_options = folders + files
                for item in file_list_options:
                    self.list_of_options.append(
                        FileListSelectionWidget(
                            icon=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                            value=path_utils.compress(item["name"]),
                        )
                    )
                    names_in_cwd.append(item["name"])
                    # TODO: find out why `await asyncio.sleep(0)` doesn't
                    #       work on large directories, and the threshold
                    #       before it stops working
                self.items_in_cwd = set(names_in_cwd)
        except PermissionError:
            self.list_of_options.append(
                Selection(
                    " Permission Error: Unable to access this directory.",
                    value="",
                    id="",
                    disabled=True,
                ),
            )
            preview = self.app.query_one("PreviewContainer")
            preview.remove_children()
            preview._current_preview_type = "none"
            preview.border_title = ""

        if len(self.list_of_options) == 1 and self.list_of_options[0].disabled:
            for selector in buttons_that_depend_on_path:
                self.app.query_one(selector).disabled = True
        else:
            for selector in buttons_that_depend_on_path:
                self.app.query_one(selector).disabled = False
        self.clear_options()
        self.add_options(self.list_of_options)
        # session handler
        self.app.query_one("#path_switcher").value = cwd + (
            "" if cwd.endswith("/") else "/"
        )
        # I question to myself why directories isn't a list[str]
        # but is a list[dict], so I'm down to take some PRs, because
        # I have other things that are more important.
        # TODO: use list[str] instead of list[dict] for directories
        if add_to_session:
            if session.historyIndex != len(session.directories) - 1:
                session.directories = session.directories[: session.historyIndex + 1]
            session.directories.append({
                "path": cwd,
            })
            if session.lastHighlighted.get(cwd) is None:
                # Hard coding is my passion (referring to the id)
                session.lastHighlighted[cwd] = (
                    self.app.query_one("#file_list").options[0].value
                )
            session.historyIndex = len(session.directories) - 1
        elif session.directories == []:
            session.directories = [{"path": path_utils.normalise(getcwd())}]
        self.app.query_one("Button#back").disabled = session.historyIndex <= 0
        self.app.query_one("Button#forward").disabled = (
            session.historyIndex == len(session.directories) - 1
        )
        try:
            if focus_on:
                self.highlighted = self.get_option_index(path_utils.compress(focus_on))
            else:
                self.highlighted = self.get_option_index(session.lastHighlighted[cwd])
        except OptionDoesNotExist:
            self.highlighted = 0
            session.lastHighlighted[cwd] = (
                self.app.query_one("#file_list").options[0].value
            )
        except KeyError:
            self.highlighted = 0
            session.lastHighlighted[cwd] = (
                self.app.query_one("#file_list").options[0].value
            )

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

    @work(exclusive=True)
    async def dummy_update_file_list(
        self,
        cwd: str,
    ) -> None:
        """Update the file list with the current directory contents.

        Args:
            cwd (str): The current working directory.
        """
        self.enter_into = cwd
        # Separate folders and files
        self.list_of_options = []

        try:
            folders, files = await path_utils.get_cwd_object(
                cwd, config["settings"]["show_hidden_files"]
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
                            value=path_utils.compress(item["name"]),
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

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        # Get the filename from the option id
        event.prevent_default()
        cwd = path_utils.normalise(getcwd())
        # Get the selected option
        selected_option = self.highlighted_option
        file_name = path_utils.decompress(selected_option.value)
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
                if self.app._chooser_file:
                    self.app.action_quit()
                else:
                    path_utils.open_file(self.app, target_path)
                if self.highlighted is None:
                    self.highlighted = 0
                self.app.tabWidget.active_tab.selectedItems = []
        elif not self.select_mode_enabled:
            full_path = path.join(cwd, file_name)
            if path.isdir(full_path):
                self.app.cd(full_path)
            else:
                if self.app._chooser_file:
                    self.app.action_quit()
                else:
                    path_utils.open_file(self.app, full_path)
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
        assert isinstance(event.option, FileListSelectionWidget)
        self.update_border_subtitle()
        # Get the highlighted option
        highlighted_option = event.option
        self.app.tabWidget.active_tab.session.lastHighlighted[
            path_utils.normalise(getcwd())
        ] = highlighted_option.value
        # Get the filename from the option id
        file_name = path_utils.decompress(highlighted_option.value)
        # total files as footer
        if self.highlighted is None:
            self.highlighted = 0
        # preview
        self.app.query_one("PreviewContainer").show_preview(
            path_utils.normalise(path.join(getcwd(), file_name))
        )
        self.app.query_one("MetadataContainer").update_metadata(event.option.dir_entry)
        self.app.query_one("#unzip").disabled = not file_name.lower().endswith(
            ARCHIVE_EXTENSIONS_FULL
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
        cwd = path_utils.normalise(getcwd())
        if not self.select_mode_enabled:
            return [
                str(
                    path_utils.normalise(
                        path.join(
                            cwd,
                            path_utils.decompress(self.highlighted_option.value),
                        )
                    )
                )
            ]
        else:
            if not self.selected:
                return []

            return [
                str(path_utils.normalise(path.join(cwd, path_utils.decompress(value))))
                for value in self.selected
            ]

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the file list."""
        if not self.dummy:
            match event.key:
                # toggle select mode
                case key if key in config["keybinds"]["toggle_visual"]:
                    event.stop()
                    await self.toggle_mode()
                case key if key in config["keybinds"]["toggle_all"]:
                    event.stop()
                    if not self.select_mode_enabled:
                        await self.toggle_mode()
                    if len(self.selected) == len(self.options):
                        self.deselect_all()
                    else:
                        self.select_all()
                case key if (
                    self.select_mode_enabled and key in config["keybinds"]["select_up"]
                ):
                    event.stop()
                    if self.get_option_at_index(0).disabled:
                        return
                    """Select the current and previous file."""
                    if self.highlighted == 0:
                        self.select(self.get_option_at_index(0))
                    else:
                        self.select(self.highlighted_option)
                        self.action_cursor_up()
                        self.select(self.highlighted_option)
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_down"]
                ):
                    event.stop()
                    if self.get_option_at_index(0).disabled:
                        return
                    """Select the current and next file."""
                    if self.highlighted == len(self.options) - 1:
                        self.select(self.get_option_at_index(self.option_count - 1))
                    else:
                        self.select(self.highlighted_option)
                        self.action_cursor_down()
                        self.select(self.highlighted_option)
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_page_up"]
                ):
                    event.stop()
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
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_page_down"]
                ):
                    event.stop()
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
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_home"]
                ):
                    event.stop()
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
                    return
                case key if (
                    self.select_mode_enabled and key in config["keybinds"]["select_end"]
                ):
                    event.stop()
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
                    return
                case key if (
                    config["plugins"]["editor"]["enabled"]
                    and key in config["plugins"]["editor"]["keybinds"]
                ):
                    event.stop()
                    if self.highlighted_option and self.highlighted_option.disabled:
                        return
                    if path.isdir(
                        path.join(
                            getcwd(),
                            path_utils.decompress(self.highlighted_option.value),
                        )
                    ):
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["folder_executable"]} "{path.join(getcwd(), path_utils.decompress(self.highlighted_option.value))}"'
                            )
                    else:
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["file_executable"]} "{path.join(getcwd(), path_utils.decompress(self.highlighted_option.value))}"'
                            )
                # hit buttons with keybinds
                case key if (
                    not self.select_mode_enabled
                    and key in config["keybinds"]["hist_previous"]
                ):
                    event.stop()
                    if self.app.query_one("#back").disabled:
                        self.app.query_one("UpButton").on_button_pressed(Button.Pressed)
                    else:
                        self.app.query_one("BackButton").on_button_pressed(
                            Button.Pressed
                        )
                case key if (
                    not self.select_mode_enabled
                    and event.key in config["keybinds"]["hist_next"]
                    and not self.app.query_one("#forward").disabled
                ):
                    event.stop()
                    self.app.query_one("ForwardButton").on_button_pressed(
                        Button.Pressed
                    )
                case key if (
                    not self.select_mode_enabled
                    and event.key in config["keybinds"]["up_tree"]
                ):
                    event.stop()
                    self.app.query_one("UpButton").on_button_pressed(Button.Pressed)
                case key if event.key in config["keybinds"]["copy_path"]:
                    event.stop()
                    await self.app.query_one("PathCopyButton").on_button_pressed(
                        Button.Pressed
                    )
                # Toggle pin on current directory
                case key if key in config["keybinds"]["toggle_pin"]:
                    event.stop()
                    pin_utils.toggle_pin(path.basename(getcwd()), getcwd())
                    await self.app.query_one("PinnedSidebar").reload_pins()
                case key if key in config["keybinds"]["copy"]:
                    event.stop()
                    await self.app.query_one("#copy").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["cut"]:
                    event.stop()
                    await self.app.query_one("#cut").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["paste"]:
                    event.stop()
                    await self.app.query_one("#paste").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["new"]:
                    event.stop()
                    self.app.query_one("#new").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["rename"]:
                    event.stop()
                    self.app.query_one("#rename").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["delete"]:
                    event.stop()
                    await self.app.query_one("#delete").on_button_pressed(
                        Button.Pressed
                    )
                case key if key in config["keybinds"]["zip"]:
                    event.stop()
                    self.app.query_one("#zip").on_button_pressed(Button.Pressed)
                case key if key in config["keybinds"]["unzip"]:
                    event.stop()
                    if not self.app.query_one("#unzip").disabled:
                        self.app.query_one("#unzip").on_button_pressed(Button.Pressed)
                # search
                case key if key in config["keybinds"]["focus_search"]:
                    event.stop()
                    self.input.focus()
                # toggle hidden files
                case key if key in config["keybinds"]["toggle_hidden_files"]:
                    event.stop()
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


class FileListRightClickOptionList(OptionList):
    def __init__(
        self, file_list: FileList, classes: str | None = None, id: str | None = None
    ) -> None:
        # Only show unzip option for archive files
        super().__init__(
            Option(f" {icon_utils.get_icon('general', 'copy')[0]} Copy", id="copy"),
            Option(f" {icon_utils.get_icon('general', 'cut')[0]} Cut", id="cut"),
            Option(
                f" {icon_utils.get_icon('general', 'delete')[0]} Delete ", id="delete"
            ),
            Option(
                f" {icon_utils.get_icon('general', 'rename')[0]} Rename ", id="rename"
            ),
            Option(f" {icon_utils.get_icon('general', 'zip')[0]} Zip", id="zip"),
            Option(f" {icon_utils.get_icon('general', 'open')[0]} Unzip", id="unzip"),
            id=id,
            classes=classes,
        )
        self.file_list = file_list

    async def on_mount(self) -> None:
        self.styles.layer = "overlay"

    async def on_key(self, event: events.Key) -> None:
        # Close menu on Escape
        if event.key == "escape":
            self.remove()
            # Return focus to file list
            self.file_list.focus()

    def update_location(self, event: events.Click) -> None:
        self.styles.offset = (event.screen_x, event.screen_y)

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
        self.add_class("hidden")
        self.file_list.focus()

    @on(events.MouseMove)
    def highlight_follow_mouse(self, event: events.MouseMove) -> None:
        hovered_option: int | None = event.style.meta.get("option")
        if hovered_option is not None and not self._options[hovered_option].disabled:
            self.highlighted = hovered_option

    @on(events.Show)
    def force_highlight_option(self, event: events.Show) -> None:
        self.file_list.add_class("-popup-shown")

    @on(events.Hide)
    def unforce_highlight_option(self, event: events.Hide) -> None:
        self.file_list.remove_class("-popup-shown")
