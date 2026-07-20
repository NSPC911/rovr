from datetime import datetime
from typing import Callable, ClassVar

from pytrash import RecycleBin, TrashEntry
from rich.cells import cell_len
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widgets import Button, SelectionList
from textual.widgets.selection_list import Selection

from rovr.classes.mixins import (
    Action,
    Actionable,
    CheckboxRenderingMixin,
    DetailColumnRenderingMixin,
    SetOptionsSelectionList,
    SingleLineOptionLayoutMixin,
)
from rovr.functions import details as detail_utils
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.utils import dismiss, get_shortest_bind, natural_size
from rovr.variables.constants import bindings, config
from rovr.variables.maps import RovrVars

restore_bind = get_shortest_bind(config["keybinds"]["trash"]["restore"])
purge_bind = get_shortest_bind(config["keybinds"]["trash"]["purge"])
empty_bind = get_shortest_bind(config["keybinds"]["trash"]["empty"])
cancel_bind = get_shortest_bind(config["keybinds"]["trash"]["cancel"])

home = path_utils.normalise(RovrVars.HOME)

_datetime_format = config["metadata"]["datetime_format"]
TRASH_COLUMNS: tuple[detail_utils.DetailColumn, ...] = (
    detail_utils.DetailColumn(
        "mtime",
        "Deleted",
        max(7, cell_len(datetime.now().strftime(_datetime_format))),
        _datetime_format,
    ),
    detail_utils.DetailColumn("size", "Size", 9, ""),
)


class TrashSelection(Selection):
    """A recycle bin entry that can render its stats as detail columns."""

    def __init__(self, prompt: Text, value: str, entry: TrashEntry) -> None:
        super().__init__(prompt, value)
        self.entry = entry

    def detail_cells(
        self, columns: tuple[detail_utils.DetailColumn, ...]
    ) -> tuple[str, ...]:
        """Format one fixed-width cell per column for this entry.

        Returns:
            tuple[str, ...]: One padded cell per column.
        """
        cells: list[str] = []
        for column in columns:
            if column.type == "mtime":
                value = (
                    self.entry.deleted_at.strftime(column.format)
                    if self.entry.deleted_at
                    else "--"
                )
            elif self.entry.size is None:
                value = "--"
            else:
                value = natural_size(
                    self.entry.size,
                    config["metadata"]["filesize_suffix"],
                    config["metadata"]["filesize_decimals"],
                )
            cells.append(detail_utils._pad(value, column.width))
        return tuple(cells)


class TrashSelectionList(
    Actionable,
    CheckboxRenderingMixin,
    DetailColumnRenderingMixin,
    SingleLineOptionLayoutMixin,
    SetOptionsSelectionList,
    SelectionList,
    inherit_bindings=False,
):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "trash--detail-size",
        "trash--detail-mtime",
    }

    ACTIONS = [
        Action(name, config["keybinds"][name])
        for name in (
            "select_up",
            "select_down",
            "select_page_up",
            "select_page_down",
            "select_home",
            "select_end",
            "toggle_all",
        )
    ]

    DETAIL_COMPONENT_PREFIX = "trash--detail-"

    @property
    def highlighted_option(self) -> Selection | None:
        if self.highlighted is not None and 0 <= self.highlighted < self.option_count:
            return self.get_option_at_index(self.highlighted)
        return None

    def render_line(self, y: int) -> Strip:
        return self.render_detail_columns(super().render_line(y), y, TRASH_COLUMNS)

    def action_toggle_select_item(self) -> None:
        if self.highlighted_option is not None:
            self.action_select()

    def action_select_up(self) -> None:
        """Select the current and previous entry."""
        if self.highlighted_option is None:
            return
        if self.highlighted == 0:
            self.select(self.get_option_at_index(0))
        else:
            self.select(self.highlighted_option)
            self.action_cursor_up()
            if self.highlighted_option is not None:
                self.select(self.highlighted_option)

    def action_select_down(self) -> None:
        """Select the current and next entry."""
        if self.highlighted_option is None:
            return
        if self.highlighted == self.option_count - 1:
            self.select(self.get_option_at_index(self.option_count - 1))
        else:
            self.select(self.highlighted_option)
            self.action_cursor_down()
            if self.highlighted_option is not None:
                self.select(self.highlighted_option)

    def _select_range_to(self, mover: Callable[[], None]) -> None:
        if self.highlighted_option is None:
            return
        old = self.highlighted or 0
        mover()
        new = self.highlighted or 0
        for index in range(min(old, new), max(old, new) + 1):
            self.select(self.get_option_at_index(index))

    def action_select_page_up(self) -> None:
        """Select every entry between the current one and a page up."""
        self._select_range_to(self.action_page_up)

    def action_select_page_down(self) -> None:
        """Select every entry between the current one and a page down."""
        self._select_range_to(self.action_page_down)

    def action_select_home(self) -> None:
        """Select every entry between the current one and the first."""
        self._select_range_to(self.action_first)

    def action_select_end(self) -> None:
        """Select every entry between the current one and the last."""
        self._select_range_to(self.action_last)

    def action_toggle_all(self) -> None:
        if self.highlighted_option:
            if len(self.selected) == len(self.options):
                self.deselect_all()
            else:
                self.select_all()


class TrashScreen(Actionable, ModalScreen):
    """Screen with a dialog to browse, restore and purge recycle bin entries."""

    def __init__(self) -> None:
        super().__init__()
        self.recycle_bin = RecycleBin()
        self.entries: list[TrashEntry] = []
        self._by_handle: dict[str, TrashEntry] = {}
        self.changed = False
        self.ACTIONS = [
            Action("cancel", config["keybinds"]["trash"]["cancel"]),
            Action("restore", config["keybinds"]["trash"]["restore"]),
            Action("purge", config["keybinds"]["trash"]["purge"]),
            Action("empty", config["keybinds"]["trash"]["empty"]),
        ]

    def _entries_list(self) -> "TrashSelectionList":
        return self.query_one("#trash_entries", TrashSelectionList)

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield TrashSelectionList(id="trash_entries")
            yield Button(
                f"\\[{restore_bind}] Restore",
                variant="success",
                id="restore",
                disabled=True,
            )
            yield Button(
                f"\\[{purge_bind}] Purge", variant="error", id="purge", disabled=True
            )
            yield Button(
                f"\\[{empty_bind}] Empty", variant="error", id="empty", disabled=True
            )
            yield Button(f"\\[{cancel_bind}] Close", variant="primary", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#dialog").border_title = "Recycle Bin"
        self.reload_entries()

    @staticmethod
    def _handle_of(entry: TrashEntry, index: int) -> str:
        return entry._handle or f"__idx_{index}"

    @staticmethod
    def _entry_icon(entry: TrashEntry) -> tuple[str, str]:
        if entry.original_path is not None and entry.is_dir:
            return icon_utils.get_icon_for_folder(entry.name, is_symlink=False)
        return icon_utils.get_icon_for_file(entry.name, is_symlink=False)

    def _format_entry(self, entry: TrashEntry) -> Text:
        from os import path

        if entry.original_path is not None and entry.is_dir:
            icon, color = icon_utils.get_icon_for_folder(entry.name, is_symlink=False)
        else:
            icon, color = icon_utils.get_icon_for_file(entry.name, is_symlink=False)

        # need to start with empty so no color is used
        prompt = Text(" ")
        prompt.append_tokens([(icon, color or ""), (" ", "")])
        if entry.original_path:
            location = path_utils.normalise(entry.original_path)
            if location == home:
                location = "~"
            if location.startswith(f"{home}/"):
                location = f"~{location[len(home) :]}"
            prompt.append_tokens([
                (f"{path.dirname(location)}/", "dim"),
                (entry.name, ""),
            ])
        return prompt

    @work(thread=True)
    def reload_entries(self) -> None:
        selection_list = self.query_one("#trash_entries", TrashSelectionList)

        prev_handle: str | None = None
        prev_index = selection_list.highlighted
        if prev_index is not None and 0 <= prev_index < selection_list.option_count:
            prev_handle = selection_list.get_option_at_index(prev_index).value
        prev_scroll = selection_list.scroll_offset.y

        try:
            self.entries = self.recycle_bin.entries()
        except PermissionError as exc:
            # happens for macos when the user has not granted access to the trash folder
            self.notify(
                str(exc),
                title="Recycle Bin",
                severity="error",
                markup=False,
            )
            return
        self._by_handle = {
            self._handle_of(entry, index): entry
            for index, entry in enumerate(self.entries)
        }
        self.app.call_from_thread(
            selection_list.set_options,
            [
                TrashSelection(
                    self._format_entry(entry), self._handle_of(entry, index), entry
                )
                for index, entry in enumerate(self.entries)
            ],
        )

        new_index: int | None = None
        if prev_handle is not None and prev_handle in self._by_handle:
            new_index = list(self._by_handle).index(prev_handle)
        elif prev_index is not None and self.entries:
            new_index = min(prev_index, len(self.entries) - 1)
        if new_index is not None:
            selection_list.highlighted = new_index
            self.call_after_refresh(
                selection_list.scroll_to, None, prev_scroll, animate=False
            )

        self.app.call_next(
            setattr,
            self.query_one("#dialog"),
            "border_subtitle",
            f"{len(self.entries)} item{'s' if len(self.entries) != 1 else ''}",
        )
        for button_id in ("#restore", "#purge"):
            self.query_one(button_id, Button).disabled = not selection_list.selected
        self.query_one("#empty", Button).disabled = not self.entries

    @on(SelectionList.SelectedChanged)
    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        for button_id in ("#restore", "#purge"):
            self.query_one(
                button_id, Button
            ).disabled = not event.selection_list.selected

    def _selected_entries(self) -> list[TrashEntry]:
        selection_list = self.query_one("#trash_entries", TrashSelectionList)
        return [
            self._by_handle[handle]
            for handle in selection_list.selected
            if handle in self._by_handle
        ]

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            self.action_cancel(event)

    @on(Button.Pressed, "#restore")
    def action_restore(self, event: Message | None = None) -> None:
        if event is not None:
            event.stop()
        entries = self._selected_entries()
        if not entries:
            self.notify(
                "No entries selected to restore.",
                title="Recycle Bin",
                severity="warning",
            )
            return
        self._run_operation("restore", entries)

    @on(Button.Pressed, "#purge")
    def action_purge(self, event: Message | None = None) -> None:
        if event is not None:
            event.stop()
        entries = self._selected_entries()
        if not entries:
            self.notify(
                "No entries selected to purge.",
                title="Recycle Bin",
                severity="warning",
            )
            return
        self._confirm_and_purge(entries)

    @on(Button.Pressed, "#empty")
    def action_empty(self, event: Message | None = None) -> None:
        if event is not None:
            event.stop()
        if not self.entries:
            return
        self._confirm_and_empty()

    @on(Button.Pressed, "#cancel")
    def action_cancel(self, event: Message | None = None) -> None:
        dismiss(self, self.changed, event)

    @work
    async def _confirm_and_purge(self, entries: list[TrashEntry]) -> None:
        from rovr.screens import YesOrNo

        confirmed = await self.app.push_screen_wait(
            YesOrNo(
                f"Permanently delete {len(entries)} entr"
                f"{'ies' if len(entries) != 1 else 'y'}? This cannot be undone.",
                destructive=True,
            )
        )
        if confirmed:
            self._run_operation("purge", entries)

    @work
    async def _confirm_and_empty(self) -> None:
        from rovr.screens import YesOrNo

        confirmed = await self.app.push_screen_wait(
            YesOrNo(
                "Permanently empty the entire recycle bin? This cannot be undone.",
                destructive=True,
            )
        )
        if confirmed:
            self._run_operation("empty", [])

    @work(thread=True)
    def _run_operation(self, operation: str, entries: list[TrashEntry]) -> None:
        try:
            match operation:
                case "restore":
                    self.recycle_bin.restore(entries)
                    self.changed = True
                case "purge":
                    self.recycle_bin.purge(entries)
                case "empty":
                    self.recycle_bin.empty()
        except (OSError, FileNotFoundError, FileExistsError) as exc:
            self.notify(
                f"Failed to {operation}: {exc}",
                title="Recycle Bin",
                severity="error",
                markup=False,
            )
        self.reload_entries()
