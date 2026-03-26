from contextlib import suppress
from os import getcwd, path
from typing import Callable, ClassVar, Iterable, Self, Sequence

from textual import events, on, work
from textual.binding import BindingType
from textual.content import ContentText
from textual.css.query import NoMatches
from textual.geometry import Region
from textual.style import Style as TextualStyle
from textual.widgets import Button, Input, OptionList, SelectionList
from textual.widgets.option_list import Option, OptionDoesNotExist
from textual.widgets.selection_list import Selection, SelectionType

from rovr.classes.mixins import CheckboxRenderingMixin
from rovr.classes.session_manager import SessionManager
from rovr.classes.textual_options import FileListSelectionWidget
from rovr.components import PopupOptionList
from rovr.functions import icons as icon_utils
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


class FileList(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    """
    OptionList but can multi-select files and folders.
    """

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
                session.directories = session.directories[: session.historyIndex + 1]
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
                # leaving this as an architectural marvel
                # worker = path_utils.threaded_get_cwd_object(
                #     self,
                #     cwd,
                #     config["interface"]["show_hidden_files"],
                #     sort_by=sort_by,
                #     reverse=sort_descending,
                # )
                # try:
                #     await worker.wait()
                # except WorkerError:
                #     return
                # if isinstance(worker.result, PermissionError):
                #     raise worker.result
                # folders, files = cast(
                #     tuple[
                #         list[path_utils.CWDObjectReturnDict],
                #         list[path_utils.CWDObjectReturnDict],
                #     ],
                #     worker.result,
                # )
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

                    self.list_of_options = [
                        FileListSelectionWidget(
                            icon=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                            clipboard=self.app.Clipboard,
                        )
                        for item in file_list_options
                    ]
                    name_to_index: dict[str, int] = {
                        item["name"]: i for i, item in enumerate(file_list_options)
                    }
                    self.items_in_cwd = set(name_to_index)
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
                # this shouldnt happen, but just in case
                self.app.query_one("#new").disabled = True

            # special check for up tree
            self.app.query_one("#up").disabled = cwd == path.dirname(cwd)

            self.set_options(self.list_of_options)
            # fix selected options
            if has_selected and name_to_index:
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
                    session.lastHighlighted[cwd] = {
                        "name": self.list_of_options[0].dir_entry.name,
                        "index": 0,
                    }
            elif session.directories == []:
                session.directories = [path_utils.normalise(getcwd())]
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
            if clear_search:
                self.app.tabWidget.active_tab.session.search = ""
            if not add_to_session:
                self.input.clear_selected()
            if self.list_of_options[0].disabled:  # special option
                if self.select_mode_enabled:
                    await self.toggle_mode()
                self.call_later(self.update_border_subtitle)
        finally:
            self.file_list_pause_check = False
            if callback:
                callback()

    @work(thread=True)
    def update_from_session(
        self, session: SessionManager, name_to_index: dict[str, int]
    ) -> None:
        # so far dont seem to have any issues when running this in a thread
        # but if it does, remove the decorator
        self.log("Restoring selected items from session...")
        self.log(session.selectedItems)
        with self.prevent(SelectionList.SelectedChanged):
            self.deselect_all()
            for item in session.selectedItems:
                if item["name"] in name_to_index:
                    self.select(self.list_of_options[name_to_index[item["name"]]])
                else:
                    to_select = min(item["index"], len(self.list_of_options) - 1)
                    self.select(self.list_of_options[to_select].id)

    async def file_selected_handler(self, target_path: str) -> None:
        if self.app._chooser_file:
            self.app.action_quit()
        elif config["settings"]["editor"]["open_all_in_editor"]:
            editor_config = config["settings"]["editor"]["file"]

            def on_error(message: str, title: str) -> None:
                self.notify(message, title=title, severity="error", markup=False)

            try:
                utils.run_editor_command(self.app, editor_config, target_path, on_error)
            except Exception as exc:
                path_utils.dump_exc(self, exc)
                self.notify(
                    f"{type(exc).__name__}: {exc}",
                    title="Error launching editor",
                    severity="error",
                    markup=False,
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
                self.app.cd(target_path, clear_search=True)
                self.app.tabWidget.active_tab.selectedItems = []
                self.app.file_list.focus()
            else:
                await self.file_selected_handler(target_path)
                if self.highlighted is None:
                    self.highlighted = 0
                self.app.tabWidget.active_tab.selectedItems = []
        elif not self.select_mode_enabled:
            full_path = path.join(cwd, file_name)
            if path.isdir(full_path):
                self.app.cd(full_path, clear_search=True)
            else:
                await self.file_selected_handler(full_path)
            if self.highlighted is None:
                self.highlighted = 0
            self.app.tabWidget.active_tab.selectedItems = []
        else:
            # self.app.tabWidget.active_tab.session.selectedItems = self.selected.copy()
            selected_ids = self.selected.copy()
            session: SessionManager = self.app.tabWidget.active_tab.session
            session.selectedItems = []
            for selected_id in selected_ids:
                option = self.get_option(selected_id)
                session.selectedItems.append({
                    "name": option.dir_entry.name,
                    "index": self.options.index(option),
                })

    # No clue why I'm using an OptionList method for SelectionList
    def on_option_list_option_highlighted(
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
        self.call_later(self.update_border_subtitle)
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
        self.app.query_one("#unzip").disabled = not utils.is_archive(
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

    def update_dimmed_items(self, paths: list[str] | None = None) -> None:
        """Update the dimmed items in the file list based on the cut items.

        Args:
            paths (list[str]): The list of paths to dim.
        """
        if paths is None:
            paths = []
        if self.option_count == 0 or self.get_option_at_index(0).disabled:
            return
        for option in self.options:
            if path_utils.normalise(option.dir_entry.path) in paths:
                option._set_prompt(option.prompt.stylize("dim"))
            else:
                option._set_prompt(option.prompt.stylize(TextualStyle(dim=False)))
        self._clear_caches()
        self._update_lines()
        self.refresh()

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the file list."""
        if self.dummy:
            return
        from rovr.functions.utils import check_key

        # hit buttons with keybinds
        if check_key(event, config["keybinds"]["hist_previous"]):
            self.action_hist_previous()
        elif check_key(event, config["keybinds"]["hist_next"]):
            self.action_hist_next()
        elif check_key(event, config["keybinds"]["up_tree"]):
            self.action_up_tree()
        elif check_key(event, config["keybinds"]["bypass_up_tree"]):
            self.action_bypass_up_tree()
        elif check_key(event, config["keybinds"]["bypass_down_tree"]):
            self.action_bypass_down_tree()
        # Toggle pin on current directory
        elif check_key(event, config["keybinds"]["toggle_pin"]):
            self.action_toggle_pin()
        elif check_key(event, config["keybinds"]["copy"]):
            self.action_copy()
        elif check_key(event, config["keybinds"]["extra_copy"]["open_popup"]):
            await self.action_extra_copy_open_popup()
        elif check_key(event, config["keybinds"]["cut"]):
            self.action_cut()
        elif check_key(event, config["keybinds"]["paste"]):
            self.action_paste()
        elif check_key(event, config["keybinds"]["new"]):
            self.action_new()
        elif check_key(event, config["keybinds"]["rename"]):
            self.action_rename()
        elif check_key(event, config["keybinds"]["delete"]):
            self.action_delete()
        elif check_key(event, config["keybinds"]["zip"]):
            self.action_zip()
        elif check_key(event, config["keybinds"]["unzip"]):
            self.action_unzip()
        # search
        elif check_key(event, config["keybinds"]["focus_search"]):
            self.action_focus_search()
        # toggle hidden files
        elif check_key(event, config["keybinds"]["toggle_hidden_files"]):
            await self.action_toggle_hidden_files()
        elif check_key(event, config["keybinds"]["change_sort_order"]["open_popup"]):
            await self.action_change_sort_order_open_popup()
        elif check_key(event, config["keybinds"]["toggle_visual"]):
            await self.action_toggle_visual()
        elif check_key(event, config["keybinds"]["toggle_all"]):
            await self.action_toggle_all()
        elif check_key(event, config["keybinds"]["select_up"]):
            self.action_select_up()
        elif check_key(event, config["keybinds"]["select_down"]):
            self.action_select_down()
        elif check_key(event, config["keybinds"]["select_page_up"]):
            self.action_select_page_up()
        elif check_key(event, config["keybinds"]["select_page_down"]):
            self.action_select_page_down()
        elif check_key(event, config["keybinds"]["select_home"]):
            self.action_select_home()
        elif check_key(event, config["keybinds"]["select_end"]):
            self.action_select_end()
        elif check_key(event, config["keybinds"]["open_editor"]):
            self.action_open_editor()

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

    def set_options(
        self,
        options: Iterable[
            Selection[SelectionType]
            | tuple[ContentText, SelectionType]
            | tuple[ContentText, SelectionType, bool]
        ],
    ) -> Self:  # ty: ignore[invalid-method-override]
        # Okay, lemme make myself clear here.
        # A PR for this is already open at
        # https://github.com/Textualize/textual/pull/6224
        # essentially, the issue is that there isnt a set_options
        # method for SelectionList, only for OptionList, but using
        # OptionList's set_options doesnt clear selected or values
        # but nothing was done, so I added it myself.
        self._selected.clear()
        self._values.clear()
        # the ty ignore is important here, because options
        # should be a Iterable["Option | VisualType | None"]
        # but that isnt the case (based on the signature)
        # so ty is crashing out.
        super().set_options(options)  # ty: ignore[invalid-argument-type]
        return self

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
                utils.run_editor_command(
                    self.app,
                    editor_config,
                    target_path,
                    lambda message, title: self.notify(
                        message=message, title=title, severity="error", markup=False
                    ),
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
            rightclickoptionlist: FileListRightClickOptionList = self.app.query_one(
                FileListRightClickOptionList
            )
        except NoMatches:
            # it happens, but I really cannot be bothered to figure it out
            rightclickoptionlist = FileListRightClickOptionList(classes="hidden")
            await self.app.mount(rightclickoptionlist)
        rightclickoptionlist.remove_class("hidden")
        if event is None:
            event = events.Click(
                self,
                (self.app.size.width - 12) // 2,
                (self.app.size.height - 8) // 2,
                0,
                0,
                3,
                False,
                False,
                False,
            )
        rightclickoptionlist.update_location(event)
        rightclickoptionlist.focus()


class FileListRightClickOptionList(PopupOptionList):
    def __init__(self, classes: str | None = None, id: str | None = None) -> None:
        # Only show unzip option for archive files
        super().__init__(
            id=id,
            classes=classes,
        )

    @on(events.Show)
    def on_show(self) -> None:
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
                disabled=not utils.is_archive(
                    self.app.file_list.highlighted_option.dir_entry.path
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
                self.file_list.action_copy()
            case "cut":
                self.file_list.action_cut()
            case "delete":
                self.file_list.action_delete()
            case "rename":
                self.file_list.action_rename()
            case "zip":
                self.file_list.action_zip()
            case "unzip":
                self.file_list.action_unzip()
            case _:
                return
        self.go_hide()
