import shlex
from contextlib import suppress
from os import getcwd, path, scandir
from typing import Callable, ClassVar, Sequence

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style
from textual import events, work
from textual.binding import BindingType
from textual.color import Color
from textual.css.query import NoMatches
from textual.errors import NoWidget
from textual.strip import Strip
from textual.widgets import Button, Input, OptionList, SelectionList
from textual.widgets.option_list import OptionDoesNotExist
from textual.widgets.selection_list import Selection
from textual.worker import get_current_worker

from rovr.classes.mixins import (
    Action,
    Actionable,
    CheckboxRenderingMixin,
    ScrollOffMixin,
    SetOptionsSelectionList,
    SingleLineOptionLayoutMixin,
)
from rovr.classes.session_manager import SessionManager, SessionOptionDict
from rovr.classes.textual_options import FileListSelectionWidget
from rovr.functions import details as detail_utils
from rovr.functions import path as path_utils
from rovr.functions import pins as pin_utils
from rovr.functions import utils
from rovr.navigation_widgets import PathInput
from rovr.state_manager import StateManager
from rovr.variables.constants import (
    bindings,
    buttons_that_depend_on_path,
    config,
)

from .file_list_right_click_menu import FileListRightClickMenu


class FileList(
    Actionable,
    CheckboxRenderingMixin,
    ScrollOffMixin,
    SingleLineOptionLayoutMixin,
    SetOptionsSelectionList,
    SelectionList,
    inherit_bindings=False,
):
    """
    OptionList but can multi-select files and folders.
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "filelist--cut",
        "filelist--cut--highlighted",
        "filelist--cut--hovered",
        "filelist--broken-link",
        "filelist--broken-link--highlighted",
        "filelist--broken-link--hovered",
        "filelist--link",
        "filelist--link--highlighted",
        "filelist--link--hovered",
        "filelist--hidden",
        "filelist--hidden--highlighted",
        "filelist--hidden--hovered",
        "filelist--detail-size",
        "filelist--detail-mtime",
        "filelist--detail-atime",
        "filelist--detail-ctime",
        "filelist--detail-permissions",
        "filelist--detail-owner",
        "filelist--detail-group",
        "filelist--git-staged",
        "filelist--git-unstaged",
        "filelist--git-untracked",
    }

    ACTIONS: list[Action] = [
        Action(action, config["keybinds"][action])
        for action in (
            "hist_previous",
            "hist_next",
            "up_tree",
            "bypass_up_tree",
            "bypass_down_tree",
            "toggle_pin",
            "copy",
            "cut",
            "paste",
            "new",
            "bulk_create",
            "rename",
            "delete",
            "zip",
            "unzip",
            "focus_search",
            "toggle_hidden_files",
            "toggle_visual",
            "toggle_all",
            "select_up",
            "select_down",
            "select_page_up",
            "select_page_down",
            "select_home",
            "select_end",
            "open",
            "open_editor",
            "open_right_click_menu",
        )
    ] + [
        Action("extra_copy_open_popup", config["keybinds"]["extra_copy"]["open_popup"]),
        Action(
            "change_sort_order_open_popup",
            config["keybinds"]["change_sort_order"]["open_popup"],
        ),
    ]

    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(
        self,
        dummy: bool = False,
        enter_into: str = "",
        select: bool = False,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """
        Initialize the FileList widget.
        Args:
            dummy (bool): Whether this is a dummy file list.
            enter_into (str): The path to enter into when a folder is selected.
            select (bool): Whether the selection is select or normal.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._options: list[FileListSelectionWidget] = []
        self.dummy = dummy
        self.enter_into = enter_into
        self.select_mode_enabled = select
        if not self.dummy:
            self.items_in_cwd: set[str] = set()
        self.file_list_pause_check = False
        self._ignore_next_click: bool = False
        self._in_git_repo: bool = False

    def on_mount(self) -> None:
        if not self.dummy and self.parent:
            self.input: Input = self.parent.query_one(Input)
            self.focus()

    @property
    def highlighted_option(self) -> FileListSelectionWidget | None:
        """The currently highlighted option, or `None` if no option is highlighted.

        Returns:
            An Option, or `None`.
        """
        if self.highlighted is not None:
            return self.options[self.highlighted]
        else:
            return None

    def _detail_columns(self) -> tuple[detail_utils.DetailColumn, ...]:
        """The configured columns, with the git column hidden outside a work tree.

        Returns:
            tuple[DetailColumn, ...]: The columns to render.
        """
        columns = detail_utils.get_detail_columns()
        if not self._in_git_repo:
            columns = tuple(column for column in columns if column.type != "git")
        return columns

    def render_line(self, y: int) -> Strip:
        line = super().render_line(y)
        if self.dummy:
            return line
        columns = self._detail_columns()
        if not columns:
            return line
        width = self.scrollable_content_region.width
        fitted = detail_utils.fit_column_count(width, columns)
        if not fitted:
            return line
        try:
            option_index, _ = self._lines[self.scroll_offset.y + y]
            option = self.options[option_index]
        except (IndexError, KeyError):
            return line
        if not isinstance(option, FileListSelectionWidget):
            return line
        cells = option.detail_cells(columns)[:fitted]
        segments = list(line)
        style = (segments[-1].style if segments else None) or self.rich_style
        detail_segments: list[Segment] = []
        details_width = 1  # is 1 and not 0 because minor right padding
        for column, cell in zip(columns[:fitted], cells):
            details_width += column.width + 2
            detail_segments.append(Segment("  ", style))
            if column.type == "git":
                pad, pair = cell[:-2], cell[-2:]
                if pad:
                    detail_segments.append(Segment(pad, style))
                if pair == "??":
                    detail_segments.append(
                        Segment(
                            pair,
                            self._detail_rich_style("filelist--git-untracked", style),
                        )
                    )
                elif pair.strip():
                    detail_segments.append(
                        Segment(
                            pair[0],
                            self._detail_rich_style("filelist--git-staged", style),
                        )
                    )
                    detail_segments.append(
                        Segment(
                            pair[1],
                            self._detail_rich_style("filelist--git-unstaged", style),
                        )
                    )
                else:
                    detail_segments.append(Segment(pair, style))
            else:
                detail_segments.append(
                    Segment(
                        cell,
                        self._detail_rich_style(
                            f"filelist--detail-{column.type}", style
                        ),
                    )
                )
        detail_segments.append(Segment(" ", style))
        return Strip([
            *line.adjust_cell_length(width - details_width, style),
            *detail_segments,
        ])

    def _detail_rich_style(self, component_class: str, base: Style) -> Style:
        """The row style with the component class's foreground and text style on top.

        Returns:
            Style: The merged rich style.
        """
        visual = self.get_visual_style("option-list--option", component_class)
        foreground = visual.foreground
        if foreground is None:
            return base
        if foreground.a < 1 and base.bgcolor is not None:
            foreground = Color.from_rich_color(base.bgcolor).blend(
                foreground, foreground.a
            )
        return base + Style(
            color=foreground.rich_color,
            bold=visual.bold,
            dim=visual.dim,
            italic=visual.italic,
            underline=visual.underline,
            strike=visual.strike,
        )

    def details_header_text(self) -> str:
        """The header line aligned with the name and detail columns.

        Returns:
            str: The full-width header text.
        """
        columns = self._detail_columns()
        width = self.scrollable_content_region.width
        fitted = detail_utils.fit_column_count(width, columns)
        gutter = self._get_left_gutter_width()
        labels = "  ".join(
            detail_utils._pad(column.label, column.width) for column in columns[:fitted]
        )
        left = " " * gutter + "   Name"
        if labels:
            labels += " "
        pad = max(1, width - cell_len(left) - cell_len(labels))
        return left + " " * pad + labels

    @work(thread=True, exclusive=True, group="detail_fill")
    def fill_async_details(self) -> None:
        column_types = {column.type for column in detail_utils.get_detail_columns()} & {
            "size",
            "git",
        }
        if self.dummy or not column_types:
            return
        worker = get_current_worker()
        options = self._options
        file_options = [
            option for option in options if isinstance(option, FileListSelectionWidget)
        ]
        if not file_options:
            return
        dirty = False
        if "git" in column_types:
            cwd = path.dirname(file_options[0].dir_entry.path)
            statuses = detail_utils.git_statuses(cwd)
            in_git_repo = statuses is not None
            if in_git_repo != self._in_git_repo:
                self._in_git_repo = in_git_repo
                dirty = True
            for option in file_options:
                if worker.is_cancelled or options is not self._options:
                    return
                status = (statuses or {}).get(option.dir_entry.name, "")
                if status != option.git_status:
                    option.set_git_status(status)
                    dirty = True
        if "size" in column_types:
            for option in file_options:
                if worker.is_cancelled or options is not self._options:
                    return
                with suppress(OSError):
                    if option.dir_entry.is_dir():
                        with scandir(option.dir_entry.path) as entries:
                            option.set_folder_item_count(sum(1 for _ in entries))
                        dirty = True
        if dirty and not worker.is_cancelled:
            self.app.call_from_thread(self.refresh)
            update_header = getattr(self.parent, "update_details_header", None)
            if callable(update_header):
                self.app.call_from_thread(update_header)

    # ignore single clicks
    async def _on_click(self, event: events.Click) -> None:
        """
        React to the mouse being clicked on an item.

        Args:
            event: The click event.
        """
        event.prevent_default()
        if self._ignore_next_click:
            self._ignore_next_click = False
            return
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
            await self.action_open_right_click_menu(event)
            event.stop()

    @work(exclusive=True)
    async def update_file_list(
        self,
        add_to_session: bool = True,
        focus_on: str | None = None,
        has_selected: bool = False,
        callback: Callable | None = None,
        clear_search: bool = True,
    ) -> None:
        """Update the file list with the current directory contents.

        Args:
            add_to_session (bool): Whether to add the current directory to the session history.
            focus_on (str | None): A custom item to set the focus as.
            has_selected (bool): Whether there are selected items in the file list (used for session management).
            callback (Callable | None): A callback function to call after updating the file list.
        """
        cwd = path_utils.normalise(getcwd())

        # Query StateManager for sort preferences
        state_manager = self.app.query_one("StateManager", StateManager)
        sort_by, sort_descending = state_manager.get_sort_prefs(cwd)

        # get sessionstate
        try:
            session: SessionManager = self.app.tabWidget.active_tab.session
        except AttributeError:
            # only happens when the tabs aren't mounted
            # this means that some stupid thing happened
            # and i dont want filelist to die as well
            # because it will be called later on (because of
            # the watcher function)
            self.clear_options()
            return
        self.file_list_pause_check = True
        name_to_index: dict[str, int] = {}
        if add_to_session:
            if session.historyIndex != len(session.directories) - 1:
                while len(session.directories) > session.historyIndex + 1:
                    session.directories.pop()
            session.directories.append(cwd)
            session.historyIndex = len(session.directories) - 1
        try:
            preview = self.app.query_one("PreviewContainer")

            # Separate folders and files
            self.list_of_options: list[FileListSelectionWidget | Selection] = []
            self.items_in_cwd: set[str] = set()

            to_highlight_index: int = -1
            if not focus_on and cwd in session.lastHighlighted:
                last_highlight = session.lastHighlighted[cwd]
                focus_on = last_highlight["name"]
            try:
                # intentional, please shut up
                folders, files = path_utils.sync_get_cwd_object(
                    self,
                    cwd,
                    config["interface"]["show_hidden_files"],
                    sort_by=sort_by,
                    reverse=sort_descending,
                )
                if not folders and not files:
                    self.list_of_options.append(
                        Selection("   --no-files--", value="", disabled=True)
                    )
                    await preview.remove_children()
                    preview.border_title = ""
                else:
                    file_list_options = folders + files
                    self.list_of_options = []
                    name_to_index: dict[str, int] = {}

                    # for i, item in enumerate(file_list_options):
                    #     self.list_of_options.append(
                    #         FileListSelectionWidget(
                    #             icon=item["icon"],
                    #             label=item["name"],
                    #             dir_entry=item["dir_entry"],
                    #             clipboard=self.app.Clipboard,
                    #         )
                    #     )
                    #     name_to_index[item["name"]] = i
                    self.list_of_options = [
                        FileListSelectionWidget(
                            icon_factory=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                            clipboard=self.app.Clipboard,
                        )
                        for item in file_list_options
                    ]
                    name_to_index = {
                        item["name"]: i for i, item in enumerate(file_list_options)
                    }
                    self.items_in_cwd = set(name_to_index.keys())

                    if focus_on in name_to_index:
                        to_highlight_index = name_to_index[focus_on]

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
                preview.border_title = ""

            # Query buttons once and update disabled state based on file list status
            buttons: list[Button] = [
                self.app.query_one(selector, Button)
                for selector in buttons_that_depend_on_path
            ]
            should_disable: bool = (
                len(self.list_of_options) == 1 and self.list_of_options[0].disabled
                if self.list_of_options
                else False
            )
            for button in buttons:
                button.disabled = should_disable
            if len(self.list_of_options) > 0:
                self.app.query_one("#new").disabled = (
                    self.list_of_options[0].id == "perm"
                )
            else:
                # this shouldn't happen, but just in case
                self.app.query_one("#new").disabled = True

            # special check for up tree
            self.app.query_one("#up").disabled = cwd == path.dirname(cwd)

            self.set_options(self.list_of_options)
            self.fill_async_details()
            update_header = getattr(self.parent, "update_details_header", None)
            if callable(update_header):
                self.call_after_refresh(update_header)
            # fix selected options
            if (has_selected or self.select_mode_enabled) and name_to_index:
                self.update_from_session(session, name_to_index)
            # session handler
            self.app.query_one("#path_switcher", PathInput).value = cwd + (
                "" if cwd.endswith("/") else "/"
            )
            if add_to_session:
                if session.lastHighlighted.get(cwd) is None and isinstance(
                    self.list_of_options[0], FileListSelectionWidget
                ):
                    # Hard coding is my passion (referring to the id)
                    session.remember_highlight(
                        cwd,
                        {
                            "name": self.list_of_options[0].dir_entry.name,
                            "index": 0,
                        },
                    )
            elif not session.directories:
                session.directories.append(path_utils.normalise(getcwd()))
            self.app.query_one("Button#back").disabled = session.historyIndex <= 0
            self.app.query_one("Button#forward").disabled = (
                session.historyIndex == len(session.directories) - 1
            )
            if (
                to_highlight_index == -1
                and cwd in session.lastHighlighted
                and session.lastHighlighted[cwd]["index"]
            ):
                to_highlight_index = min(
                    len(self.list_of_options) - 1, session.lastHighlighted[cwd]["index"]
                )
            # temporary fix until i start using session.scroll_target_y
            self.scroll_target_y = 0
            try:
                self.highlighted = to_highlight_index
            except (OptionDoesNotExist, KeyError):
                self.highlighted = 0
            if isinstance(self.highlighted_option, FileListSelectionWidget):
                session.remember_highlight(
                    cwd,
                    SessionOptionDict({
                        "name": self.highlighted_option.dir_entry.name,
                        "index": self.highlighted or 0,  # weird ty behaviour on 0.0.33
                    }),
                )

            self.scroll_to_highlight()
            self.app.tabWidget.active_tab.label = (
                path.basename(cwd) if path.basename(cwd) != "" else cwd.strip("/")
            )
            self.app.tabWidget.active_tab.directory = cwd
            self.app.tabWidget.parent.on_resize()
            with self.input.prevent(self.input.Changed):
                self.input.clear()
            if clear_search:
                self.app.tabWidget.active_tab.session.search = ""
            if not add_to_session:
                self.input.clear_selected()
            if self.list_of_options[0].disabled:  # special option
                if self.select_mode_enabled:
                    await self.toggle_mode()
                self.update_border_subtitle()
        finally:
            self.file_list_pause_check = False
            if callback:
                callback()

    def update_from_session(
        self, session: SessionManager, name_to_index: dict[str, int]
    ) -> None:
        self.log("Restoring selected items from session...")
        self.log(session.selectedItems)
        with self.prevent(SelectionList.SelectedChanged):
            self.deselect_all()
            for item in session.selectedItems:
                if item["name"] in name_to_index:
                    self.select(self.list_of_options[name_to_index[item["name"]]])

    async def file_selected_handler(self, paths: list[str]) -> None:
        if self.app._chooser_file:
            self.call_next(self.app.action_quit)
            return

        if config["settings"]["editor"].get("open_all_in_editor", False):
            editor_config = config["settings"]["editor"]["file"]

            def on_error(message: str, title: str) -> None:
                self.notify(message, title=title, severity="error", markup=False)

            try:
                if isinstance(editor_config["run"], str):
                    cmd = (
                        editor_config["run"]
                        + " "
                        + " ".join(shlex.quote(p) for p in paths)
                    )
                else:
                    cmd = editor_config["run"] + paths
                utils.run_command(
                    self.app,
                    cmd,
                    run_type="orphan"
                    if editor_config.get("orphan", True)
                    else "suspend",
                    on_error=on_error,
                    shell=editor_config["shell"],
                )
            except Exception as exc:
                path_utils.dump_exc(self, exc)
                self.notify(
                    f"{type(exc).__name__}: {exc}",
                    title="Error launching editor",
                    severity="error",
                    markup=False,
                )
            return

        for target in paths:
            path_utils.run_opener(self.app, path_utils.normalise(target))

    @work
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
                self.app.cd(target_path, clear_search=True)
                self.app.tabWidget.active_tab.selectedItems = []
                self.app.file_list.focus()
            else:
                await self.file_selected_handler([target_path])
                if self.highlighted is None:
                    self.highlighted = 0
                self.app.tabWidget.active_tab.selectedItems = []
        elif not self.select_mode_enabled:
            full_path = path.join(cwd, file_name)
            if path.isdir(full_path):
                self.app.cd(full_path, clear_search=True)
            else:
                await self.file_selected_handler([full_path])
            if self.highlighted is None:
                self.highlighted = 0
            self.app.tabWidget.active_tab.selectedItems = []
        else:
            selected_ids = self.selected.copy()
            session: SessionManager = self.app.tabWidget.active_tab.session
            session.selectedItems = []
            for selected_id in selected_ids:
                option = self.get_option(selected_id)
                if not isinstance(option, FileListSelectionWidget):
                    continue
                session.selectedItems.append({
                    "name": option.dir_entry.name,
                    "index": self.options.index(option),
                })

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
        if self.app._on_mount_done:
            self.update_border_subtitle()
        else:
            self.call_after_refresh(self.update_border_subtitle)
        # Get the highlighted option
        highlighted_option = event.option
        self.app.tabWidget.active_tab.session.remember_highlight(
            path_utils.normalise(getcwd()),
            {"name": highlighted_option.dir_entry.name, "index": self.highlighted},
        )
        # Get the filename from the option id
        # total files as footer
        if self.highlighted is None:
            self.highlighted = 0
        # update tracked mtime for the watcher
        try:
            is_file = highlighted_option.dir_entry.is_file()
        except OSError:
            is_file = False
        if is_file:
            with suppress(OSError):
                self.app._highlighted_file_mtime = (
                    highlighted_option.dir_entry.stat().st_mtime
                )
        else:
            self.app._highlighted_file_mtime = None
        # preview
        self.app.query_one("MetadataContainer").update_metadata(
            event.option.dir_entry, event.option
        )
        try:
            self.app.query_one("PreviewContainer").show_preview(
                highlighted_option.dir_entry.path,
                highlighted_option.dir_entry.stat().st_mtime,
            )
        except FileNotFoundError:
            # if the file is deleted, just remove the preview and return
            await self.app.query_one("PreviewContainer").file_not_found(
                highlighted_option.dir_entry.path, highlighted_option
            )
            return
        self.app.query_one("#unzip").update_unzip_state(
            highlighted_option.dir_entry.path
        )

    @property
    def options(self) -> Sequence[FileListSelectionWidget]:
        return self._options

    async def toggle_mode(self) -> None:
        """Toggle the selection mode between select and normal."""
        if (
            self.highlighted_option
            and self.highlighted_option.disabled
            and not self.select_mode_enabled
        ):
            return
        self.select_mode_enabled = not self.select_mode_enabled
        self._line_cache.clear()
        self._option_render_cache.clear()
        self.refresh(layout=True, repaint=True)
        self.app.tabWidget.active_tab.session.selectMode = self.select_mode_enabled
        with self.prevent(SelectionList.SelectedChanged):
            self.deselect_all()
        self.update_border_subtitle()
        if self.select_mode_enabled:
            self.add_class("select-mode")
        else:
            self.remove_class("select-mode")
        update_header = getattr(self.parent, "update_details_header", None)
        if callable(update_header):
            update_header()

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
            options = (self.get_option(value) for value in values)

            return [
                str(path_utils.normalise(option.dir_entry.path))
                for option in options
                if isinstance(option, FileListSelectionWidget)
            ]

    def update_dimmed_items(self) -> None:
        """Update the dimmed items in the file list based on the cut items."""
        if self.option_count == 0 or self.get_option_at_index(0).disabled:
            return
        for option in self.options:
            option._invalidate_prompt_cache()
        self._clear_caches()
        self._update_lines()
        self.refresh()

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the file list."""
        if self.dummy:
            event.prevent_default()

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

    # not exactly sure, but there's this issue where if I click the
    # hist_previous keybind twice too fast, it registers it as once, so
    # there really is no choice, aside from using on_button_pressed :/
    def action_hist_previous(self) -> None:
        if not self.select_mode_enabled:
            if self.app.query_one("#back").disabled:
                self.app.query_one("UpButton").on_button_pressed()
            else:
                self.app.query_one("BackButton").on_button_pressed()

    def action_hist_next(self) -> None:
        if not self.select_mode_enabled and not self.app.query_one("#forward").disabled:
            self.app.query_one("ForwardButton").on_button_pressed()

    def action_up_tree(self) -> None:
        if not self.select_mode_enabled:
            self.app.query_one("UpButton").on_button_pressed()

    def action_bypass_up_tree(self) -> None:
        if not self.select_mode_enabled:
            # get parent directory, go up until theres a folder with more than one item
            to_dir = path.dirname(getcwd())
            prev_to_dir = getcwd()
            try:
                for _ in range(
                    1000
                ):  # hardcoded limitation, I don't want it to remain stuck
                    folders, files = path_utils.sync_get_cwd_object(
                        self,
                        to_dir,
                        config["interface"]["show_hidden_files"],
                        sort_by=None,
                    )
                    if len(files) != 0 or len(folders) != 1:
                        break
                    only_entry = path.join(to_dir, folders[0]["name"])
                    if not path.isdir(only_entry):
                        break
                    if to_dir == "" or to_dir == path.dirname(to_dir):
                        break
                    prev_to_dir = to_dir
                    to_dir = path.dirname(to_dir)
                self.app.cd(to_dir, clear_search=True)
            except PermissionError:
                self.app.cd(prev_to_dir, clear_search=True)

    def action_bypass_down_tree(self) -> None:
        if not self.select_mode_enabled:
            highlighted_option = self.highlighted_option
            if highlighted_option is not None:
                if highlighted_option.dir_entry.is_file():
                    return
                else:
                    to_dir = highlighted_option.dir_entry.path
                    prev_to_dir = getcwd()
                    try:
                        for _ in range(
                            1000
                        ):  # hardcoded limitation, I don't want it to remain stuck
                            folders, files = path_utils.sync_get_cwd_object(
                                self,
                                to_dir,
                                config["interface"]["show_hidden_files"],
                                sort_by=None,
                            )
                            if len(files) != 0 or len(folders) != 1:
                                break
                            next_path = folders[0]["dir_entry"].path
                            if not path.isdir(next_path):
                                break
                            prev_to_dir = to_dir
                            to_dir = next_path
                        self.app.cd(to_dir, clear_search=True)
                    except PermissionError:
                        self.app.cd(prev_to_dir, clear_search=True)

    # Unlike for Up/Down/HistBack/HistForward, there is nothing beneficial
    # if you spam the keybind for them, so I don't need to worry about
    # it being registered once instead of twice (you don't want to create
    # two items do you?)
    def action_toggle_pin(self) -> None:
        pin_utils.toggle_pin(path.basename(getcwd()), getcwd())
        with suppress(OSError):
            setattr(self.app, "_pins_mtime", path.getmtime(pin_utils.PIN_PATH))
        self.app.query_one("PinnedSidebar").reload_pins()

    def action_copy(self) -> None:
        self.app.query_one("#copy").action_press()

    async def action_extra_copy_open_popup(self) -> None:
        await self.app.query_one("#copy").action_open_popup(
            events.Key(
                key=config["keybinds"]["extra_copy"]["open_popup"][0], character=None
            )
        )

    def action_cut(self) -> None:
        self.app.query_one("#cut").action_press()

    def action_paste(self) -> None:
        self.app.query_one("#paste").action_press()

    def action_new(self) -> None:
        self.app.query_one("#new").action_press()

    async def action_bulk_create(self) -> None:
        self.app.query_one("#new").action_bulk_create()

    def action_rename(self) -> None:
        self.app.query_one("#rename").action_press()

    def action_delete(self) -> None:
        self.app.query_one("#delete").action_press()

    def action_zip(self) -> None:
        self.app.query_one("#zip").action_press()

    def action_unzip(self) -> None:
        self.app.query_one("#unzip").action_press()

    def action_focus_search(self) -> None:
        self.input.focus()

    async def action_toggle_hidden_files(self) -> None:
        """Toggle the visibility of hidden files."""
        config["interface"]["show_hidden_files"] = not config["interface"][
            "show_hidden_files"
        ]
        self.update_file_list(add_to_session=False)
        status = (
            "[$success underline]shown"
            if config["interface"]["show_hidden_files"]
            else "[$error underline]hidden"
        )
        self.app.notify(
            f"Hidden files are now {status}[/]", severity="information", timeout=2.5
        )
        assert self.parent and self.parent.parent
        if self.parent.parent.query("PreviewContainer > FileList") and not self.dummy:
            self.highlighted = self.highlighted

    async def action_change_sort_order_open_popup(self) -> None:
        await self.app.query_one("SortOrderButton").action_open_popup()

    async def action_toggle_visual(self) -> None:
        if self.highlighted_option:
            await self.toggle_mode()

    async def action_toggle_all(self) -> None:
        if self.highlighted_option:
            if self.get_option_at_index(0).disabled:
                return
            if not self.select_mode_enabled:
                await self.toggle_mode()
            if len(self.selected) == len(self.options):
                self.deselect_all()
            else:
                self.select_all()

    def action_select_up(self) -> None:
        """Select the current and previous file."""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            if self.highlighted == 0:
                self.select(self.get_option_at_index(0))
            else:
                self.select(self.highlighted_option)
                self.action_cursor_up()
                self.select(self.highlighted_option)

    def action_select_down(self) -> None:
        """Select the current and next file."""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            if self.highlighted == len(self.options) - 1:
                self.select(self.get_option_at_index(self.option_count - 1))
            else:
                self.select(self.highlighted_option)
                self.action_cursor_down()
                self.select(self.highlighted_option)

    def action_select_page_up(self) -> None:
        """Select the options between the current and the previous 'page'."""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            old = self.highlighted
            self.action_page_up()
            new = self.highlighted
            old = 0 if old is None else old
            new = 0 if new is None else new
            assert isinstance(old, int) and isinstance(new, int)
            for index in range(new, old + 1):
                self.select(self.get_option_at_index(index))

    def action_select_page_down(self) -> None:
        """Select the options between the current and the next 'page'."""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            old = self.highlighted
            self.action_page_down()
            new = self.highlighted
            old = 0 if old is None else old
            new = 0 if new is None else new
            assert isinstance(old, int) and isinstance(new, int)
            for index in range(old, new + 1):
                self.select(self.get_option_at_index(index))

    def action_select_home(self) -> None:
        """Select the options between the current and the first option"""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            old = self.highlighted
            self.action_first()
            new = self.highlighted
            old = 0 if old is None else old
            new = 0 if new is None else new
            assert isinstance(old, int) and isinstance(new, int)
            for index in range(new, old + 1):
                self.select(self.get_option_at_index(index))

    def action_select_end(self) -> None:
        """Select the options between the current and the last option"""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            old = self.highlighted
            self.action_last()
            new = self.highlighted
            old = 0 if old is None else old
            new = 0 if new is None else new
            assert isinstance(old, int) and isinstance(new, int)
            for index in range(old, new + 1):
                self.select(self.get_option_at_index(index))

    def action_toggle_select_item(self) -> None:
        """Toggle selection of the currently highlighted item in visual mode."""
        if (
            self.highlighted_option
            and self.select_mode_enabled
            and (not self.get_option_at_index(0).disabled)
        ):
            self.action_select()

    async def action_open(self) -> None:
        if self.highlighted is None:
            return
        if (
            self.highlighted_option
            and self.highlighted_option.disabled
            and not self.select_mode_enabled
        ):
            return
        cwd = path_utils.normalise(getcwd())
        if self.select_mode_enabled:
            selected_ids = self.selected.copy()
            session = self.app.tabWidget.active_tab.session
            session.selectedItems = []
            paths_to_open = []
            for selected_id in selected_ids:
                option = self.get_option(selected_id)
                if not isinstance(option, FileListSelectionWidget):
                    continue
                session.selectedItems.append({
                    "name": option.dir_entry.name,
                    "index": self.options.index(option),
                })
                full_path = path.join(cwd, option.dir_entry.name)
                if path.isdir(full_path):
                    self.app.cd(full_path, clear_search=True)
                else:
                    paths_to_open.append(full_path)
            if paths_to_open:
                await self.file_selected_handler(paths_to_open)
        else:
            option = self.highlighted_option
            if not isinstance(option, FileListSelectionWidget):
                return
            full_path = path.join(cwd, option.dir_entry.name)
            if path.isdir(full_path):
                self.app.cd(full_path, clear_search=True)
            else:
                await self.file_selected_handler([full_path])

    def action_open_editor(self) -> None:
        if (self.highlighted is not None) and not (
            self.highlighted_option and self.highlighted_option.disabled
        ):
            target_path = self.highlighted_option.dir_entry.path
            if path.isdir(target_path):
                editor_config = config["settings"]["editor"]["folder"]
            else:
                editor_config = config["settings"]["editor"]["file"]

            try:
                utils.run_command(
                    self.app,
                    utils.command(editor_config["run"], target_path),
                    run_type="orphan"
                    if editor_config.get("orphan", True)
                    else "suspend",
                    on_error=lambda message, title: self.notify(
                        message=message, title=title, severity="error", markup=False
                    ),
                    shell=editor_config["shell"],
                )
            except Exception as exc:
                path_utils.dump_exc(self, exc)
                self.notify(
                    f"{type(exc).__name__}: {exc}",
                    title="Error launching editor",
                    severity="error",
                    markup=False,
                )

    async def action_open_right_click_menu(
        self, event: events.Click | None = None
    ) -> None:
        # Show right click menu
        try:
            rightclickoptionlist: FileListRightClickMenu = self.app.query_one(
                FileListRightClickMenu
            )
        except NoMatches:
            # it happens, but I really cannot be bothered to figure it out
            rightclickoptionlist = FileListRightClickMenu()
            await self.app.mount(rightclickoptionlist)
        if event is None:
            self.scroll_to_highlight()

            try:
                visible_region = self.screen.find_widget(self).visible_region
                top_left = visible_region.offset
            except NoWidget:
                return

            if self.highlighted is not None:
                line_offset = self._index_to_line[self.highlighted]
                x = (
                    top_left.x
                    + min(
                        visible_region.width // 2,
                        len(str(self.highlighted_option.prompt)),
                    )
                    + 1
                )
                y = top_left.y + line_offset - int(self.scroll_target_y)
            else:
                x = (
                    top_left.x
                    + min(
                        visible_region.width // 2,
                        len(str(self.get_option_at_index(0).prompt)),
                    )
                    + 1
                )
                y = top_left.y + int(
                    self.scroll_target_y
                )  # why is it an addition, i have no clue

            event = events.Click(
                self,
                x,
                y,
                0,
                0,
                3,
                False,
                False,
                False,
            )
        await rightclickoptionlist.pre_show()
        rightclickoptionlist.update_location(event)
        rightclickoptionlist.display = True
        self.call_later(rightclickoptionlist.focus)
