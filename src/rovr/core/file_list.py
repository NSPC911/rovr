from os import getcwd, path
from os import system as cmd
from typing import ClassVar

from rich.segment import Segment
from rich.style import Style
from textual import events, work
from textual.binding import Binding, BindingType
from textual.geometry import Size
from textual.strip import Strip
from textual.widgets import Button, Input, OptionList, SelectionList
from textual.widgets.option_list import OptionDoesNotExist
from textual.widgets.selection_list import Selection

from rovr import utils
from rovr.options import FileListSelectionWidget
from rovr.utils import config


class FileList(SelectionList, inherit_bindings=False):
    """
    OptionList but can multi-select files and folders.
    """

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

    def on_mount(self) -> None:
        if not self.dummy:
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
            if self.highlighted == clicked_option or self.select_mode_enabled:
                self.action_select()
            else:
                self.highlighted = clicked_option

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
        cwd = utils.normalise(getcwd())
        # get sessionstate
        try:
            # only happens when the tabs aren't mounted
            session = self.app.tabWidget.active_tab.session
        except AttributeError:
            self.clear_options()
            return
        # Separate folders and files
        folders, files = utils.get_cwd_object(cwd)
        options = []
        if folders == [PermissionError] or files == [PermissionError]:
            options.append(
                Selection(
                    " Permission Error: Unable to access this directory.",
                    value="",
                    id="",
                    disabled=True,
                ),
            )
            file_list_options = [".."]
        elif folders == [] and files == []:
            options.append(Selection("   --no-files--", value="", id="", disabled=True))
            preview = self.app.query_one("PreviewContainer")
            preview.remove_children()
            preview._current_preview_type = "none"
            # nothing inside
        else:
            file_list_options = folders + files
            for item in file_list_options:
                options.append(
                    FileListSelectionWidget(
                        icon=item["icon"],
                        label=item["name"],
                        dir_entry=item["dir_entry"],
                        value=utils.compress(item["name"]),
                        id=utils.compress(item["name"]),
                    )
                )
        self.clear_options()
        self.add_options(options)
        # session handler
        self.app.query_one("#path_switcher").value = cwd + "/"
        # I question to myself why sessionDirectories isn't a list[str]
        # but is a list[dict], so I'm down to take some PRs, because
        # I have other things that are more important.
        # TODO: use list[str] instead of list[dict] for sessionDirectories
        if add_to_session:
            if session.sessionHistoryIndex != len(session.sessionDirectories) - 1:
                session.sessionDirectories = session.sessionDirectories[
                    : session.sessionHistoryIndex + 1
                ]
            session.sessionDirectories.append({
                "path": cwd,
            })
            if session.sessionLastHighlighted.get(cwd) is None:
                # Hard coding is my passion (referring to the id)
                session.sessionLastHighlighted[cwd] = (
                    self.app.query_one("#file_list").options[0].value
                )
            session.sessionHistoryIndex = len(session.sessionDirectories) - 1
        elif session.sessionDirectories == []:
            session.sessionDirectories = [{"path": utils.normalise(getcwd())}]
        self.app.query_one("Button#back").disabled = session.sessionHistoryIndex <= 0
        self.app.query_one("Button#forward").disabled = (
            session.sessionHistoryIndex == len(session.sessionDirectories) - 1
        )
        try:
            if focus_on:
                self.highlighted = self.get_option_index(utils.compress(focus_on))
            else:
                self.highlighted = self.get_option_index(
                    session.sessionLastHighlighted[cwd]
                )
        except OptionDoesNotExist:
            self.highlighted = 0
            session.sessionLastHighlighted[cwd] = (
                self.app.query_one("#file_list").options[0].value
            )
        except KeyError:
            self.highlighted = 0
            session.sessionLastHighlighted[cwd] = (
                self.app.query_one("#file_list").options[0].value
            )
        self.app.tabWidget.active_tab.label = (
            path.basename(cwd) if path.basename(cwd) != "" else cwd.strip("/")
        )
        self.app.tabWidget.active_tab.directory = cwd
        self.app.tabWidget.parent.on_resize()
        self.input.clear()

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
        self.clear_options()
        # Separate folders and files
        folders, files = utils.get_cwd_object(cwd)
        self.list_of_options = []
        if folders == [PermissionError] or files == [PermissionError]:
            self.list_of_options.append(
                Selection(
                    " Permission Error: Unable to access this directory.",
                    id="",
                    value="",
                    disabled=True,
                )
            )
        elif folders == [] and files == []:
            self.list_of_options.append(
                Selection("  --no-files--", value="", id="", disabled=True)
            )
        else:
            file_list_options = folders + files
            for item in file_list_options:
                self.list_of_options.append(
                    FileListSelectionWidget(
                        icon=item["icon"],
                        label=item["name"],
                        dir_entry=item["dir_entry"],
                        value=utils.compress(item["name"]),
                        id=utils.compress(item["name"]),
                    )
                )
        self.add_options(self.list_of_options)
        # somehow prevents more debouncing, ill take it
        self.refresh(repaint=True, layout=True)

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        # Get the filename from the option id
        event.prevent_default()
        cwd = utils.normalise(getcwd())
        # Get the selected option
        selected_option = self.get_option_at_index(self.highlighted)
        file_name = utils.decompress(selected_option.value)
        if self.dummy and path.isdir(path.join(self.enter_into, file_name)):
            # if the folder is selected, then cd there,
            # skipping the middle folder entirely
            self.app.cd(path.join(self.enter_into, file_name))
            self.app.query_one("#file_list").focus()
        elif not self.select_mode_enabled:
            # Check if it's a folder or a file
            if path.isdir(path.join(cwd, file_name)):
                # If it's a folder, navigate into it
                self.app.cd(path.join(cwd, file_name))
            else:
                utils.open_file(path.join(cwd, file_name))
            if self.highlighted is None:
                self.highlighted = 0
            utils.set_scuffed_subtitle(
                self.parent,
                "NORMAL",
                f"{self.highlighted + 1}/{self.option_count}",
            )
        else:
            utils.set_scuffed_subtitle(
                self.parent, "SELECT", f"{len(self.selected)}/{len(self.options)}"
            )

    # No clue why I'm using an OptionList method for SelectionList
    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        assert isinstance(event.option, FileListSelectionWidget)
        if self.dummy:
            return
        elif event.option.value == "HTI":
            self.app.query_one("PreviewContainer").remove_children()
            return
        if self.select_mode_enabled and self.selected is not None:
            utils.set_scuffed_subtitle(
                self.parent,
                "SELECT",
                f"{len(self.selected)}/{len(self.options)}",
            )
        elif self.selected is not None:
            utils.set_scuffed_subtitle(
                self.parent,
                "NORMAL",
                f"{self.highlighted + 1}/{self.option_count}",
            )
        # Get the highlighted option
        highlighted_option = event.option
        self.app.tabWidget.active_tab.session.sessionLastHighlighted[
            utils.normalise(getcwd())
        ] = highlighted_option.value
        # Get the filename from the option id
        file_name = utils.decompress(highlighted_option.value)
        # total files as footer
        if self.highlighted is None:
            self.highlighted = 0
        # preview
        self.app.query_one("PreviewContainer").show_preview(
            utils.normalise(path.join(getcwd(), file_name))
        )
        self.app.query_one("MetadataContainer").update_metadata(event.option.dir_entry)
        self.app.query_one("#unzip").disabled = not file_name.endswith((
            ".tar.gz",
            ".tgz",
            "tar.bz2",
            ".tbz2",
            ".tar.xz",
            ".zip",
        ))

    def _update_lines(self) -> None:
        """Update internal structures when new lines are added."""
        if not self.scrollable_content_region:
            return

        line_cache = self._line_cache
        line_cache.clear()
        padding = self.get_component_styles("option-list--option").padding
        width = self.scrollable_content_region.width - self._get_left_gutter_width()
        for index, option in enumerate(self.options):
            if not option.disabled or option.id.endswith("header") or option.id == "":
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

    # Use better versions of the checkbox icons
    def _get_left_gutter_width(
        self,
    ) -> int:
        """Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
        if self.dummy or not self.select_mode_enabled:
            return 0
        else:
            # in future, if anything was changed, you just need to add the line below
            return len(
                utils.get_toggle_button_icon("left")
                + utils.get_toggle_button_icon("inner")
                + utils.get_toggle_button_icon("right")
                + " "
            )

    def render_line(self, y: int) -> Strip:
        """Render a line in the display.

        Args:
            y: The line to render.

        Returns:
            A [`Strip`][textual.strip.Strip] that is the line to render.
        """
        line = super(SelectionList, self).render_line(y)

        if self.dummy or not self.select_mode_enabled:
            return Strip([*line])

        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return line

        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        underlying_style = next(iter(line)).style or self.rich_style
        assert underlying_style is not None

        button_style = self.get_component_rich_style(component_style)

        side_style = Style.from_color(button_style.bgcolor, underlying_style.bgcolor)

        side_style += Style(meta={"option": selection_index})
        button_style += Style(meta={"option": selection_index})

        # in future, if anything was changed, you just need to fix the segments below
        return Strip([
            Segment(utils.get_toggle_button_icon("left"), style=side_style),
            Segment(
                utils.get_toggle_button_icon("inner_filled")
                if selection.value in self._selected
                else utils.get_toggle_button_icon("inner"),
                style=button_style,
            ),
            Segment(utils.get_toggle_button_icon("right"), style=side_style),
            Segment(" ", style=underlying_style),
            *line,
        ])

    async def toggle_mode(self) -> None:
        """Toggle the selection mode between select and normal."""
        self.select_mode_enabled = not self.select_mode_enabled
        highlighted = self.highlighted
        self.update_file_list(add_to_session=False)
        self.highlighted = highlighted

    async def get_selected_objects(self) -> list[str] | None:
        """Get the selected objects in the file list.
        Returns:
            list[str]: If there are objects at that given location.
            None: If there are no objects at that given location.
        """
        cwd = utils.normalise(getcwd())
        if self.get_option_at_index(self.highlighted).value == "HTI":
            return None
        if not self.select_mode_enabled:
            return [
                utils.normalise(
                    path.join(
                        cwd,
                        utils.decompress(
                            self.get_option_at_index(self.highlighted).value
                        ),
                    )
                )
            ]
        else:
            return [
                utils.normalise(path.join(cwd, utils.decompress(option)))
                for option in self.selected
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
                    """Select the current and previous file."""
                    if self.highlighted == 0:
                        self.select(self.get_option_at_index(0))
                    else:
                        self.select(self.get_option_at_index(self.highlighted))
                        self.action_cursor_up()
                        self.select(self.get_option_at_index(self.highlighted))
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_down"]
                ):
                    event.stop()
                    """Select the current and next file."""
                    if self.highlighted == len(self.options) - 1:
                        self.select(self.get_option_at_index(self.option_count - 1))
                    else:
                        self.select(self.get_option_at_index(self.highlighted))
                        self.action_cursor_down()
                        self.select(self.get_option_at_index(self.highlighted))
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_page_up"]
                ):
                    event.stop()
                    """Select the options between the current and the previous 'page'."""
                    old = self.highlighted
                    self.action_page_up()
                    new = self.highlighted
                    if old is None:
                        old = 0
                    if new is None:
                        new = 0
                    for index in range(new, old + 1):
                        self.select(self.get_option_at_index(index))
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_page_down"]
                ):
                    event.stop()
                    """Select the options between the current and the next 'page'."""
                    old = self.highlighted
                    self.action_page_down()
                    new = self.highlighted
                    if old is None:
                        old = 0
                    if new is None:
                        new = 0
                    for index in range(old, new + 1):
                        self.select(self.get_option_at_index(index))
                    return
                case key if (
                    self.select_mode_enabled
                    and key in config["keybinds"]["select_home"]
                ):
                    event.stop()
                    old = self.highlighted
                    self.action_first()
                    new = self.highlighted
                    if old is None:
                        old = 0
                    for index in range(new, old + 1):
                        self.select(self.get_option_at_index(index))
                    return
                case key if (
                    self.select_mode_enabled and key in config["keybinds"]["select_end"]
                ):
                    event.stop()
                    old = self.highlighted
                    self.action_last()
                    new = self.highlighted
                    if old is None:
                        old = 0
                    for index in range(old, new + 1):
                        self.select(self.get_option_at_index(index))
                    return
                case key if (
                    config["plugins"]["editor"]["enabled"]
                    and key in config["plugins"]["editor"]["keybinds"]
                ):
                    event.stop()
                    if path.isdir(
                        path.join(
                            getcwd(),
                            utils.decompress(
                                self.get_option_at_index(self.highlighted).id
                            ),
                        )
                    ):
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["folder_executable"]} "{path.join(getcwd(), utils.decompress(self.get_option_at_index(self.highlighted).id))}"'
                            )
                    else:
                        with self.app.suspend():
                            cmd(
                                f'{config["plugins"]["editor"]["file_executable"]} "{path.join(getcwd(), utils.decompress(self.get_option_at_index(self.highlighted).id))}"'
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
                # Toggle pin on current directory
                case key if key in config["keybinds"]["toggle_pin"]:
                    event.stop()
                    utils.toggle_pin(path.basename(getcwd()), getcwd())
                    self.app.query_one("PinnedSidebar").reload_pins()
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
