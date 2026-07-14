import os
from typing import Callable, ClassVar

from pytrash import RecycleBin, TrashEntry
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, SelectionList
from textual.widgets.selection_list import Selection

from rovr.classes.mixins import (
    Action,
    Actionable,
    CheckboxRenderingMixin,
    SetOptionsSelectionList,
)
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.utils import dismiss, get_shortest_bind, natural_size
from rovr.variables.constants import bindings, config
from rovr.variables.maps import RovrVars

restore_bind = get_shortest_bind(config["keybinds"]["trash"]["restore"])
purge_bind = get_shortest_bind(config["keybinds"]["trash"]["purge"])
empty_bind = get_shortest_bind(config["keybinds"]["trash"]["empty"])
cancel_bind = get_shortest_bind(config["keybinds"]["trash"]["cancel"])


class TrashSelectionList(
    Actionable,
    CheckboxRenderingMixin,
    SetOptionsSelectionList,
    SelectionList,
    inherit_bindings=False,
):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

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

    @property
    def highlighted_option(self) -> Selection | None:
        if self.highlighted is not None and 0 <= self.highlighted < self.option_count:
            return self.get_option_at_index(self.highlighted)
        return None

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

    def _handle_of(self, entry: TrashEntry, index: int) -> str:
        return entry._handle or f"__idx_{index}"

    def _trashed_data_path(self, entry: TrashEntry) -> str | None:
        """Best-effort location of the trashed bytes, for icon detection.

        Only the freedesktop (Linux) layout is derivable from the private
        handle; other backends fall back to a file icon.

        Returns:
            str | None: The path to the trashed data, or None if unknown.
        """
        handle = entry._handle.replace("/", os.sep)
        marker = f"{os.sep}info{os.sep}"
        if handle.endswith(".trashinfo") and marker in handle:
            return handle[: -len(".trashinfo")].replace(
                marker, f"{os.sep}files{os.sep}"
            )
        return None

    def _entry_icon(self, entry: TrashEntry) -> tuple[str, str]:
        data_path = self._trashed_data_path(entry)
        if data_path is not None and os.path.isdir(data_path):
            return icon_utils.get_icon_for_folder(entry.name, is_symlink=False)
        return icon_utils.get_icon_for_file(entry.name, is_symlink=False)

    def _shorten_path(self, location: str) -> str:
        location = path_utils.normalise(location)
        home = path_utils.normalise(RovrVars.HOME)
        if location == home:
            return "~"
        if location.startswith(f"{home}/"):
            return f"~{location[len(home) :]}"
        return location

    def _format_entry(self, entry: TrashEntry) -> Text:
        icon, color = self._entry_icon(entry)
        # Lead with a neutral space so the checkbox gutter derives its colour
        # from the base style rather than the (coloured) file icon, matching
        # how the file list renders.
        prompt = Text(" ")
        prompt.append(icon, style=color or "")
        prompt.append(" ")
        prompt.append(entry.name)
        meta: list[str] = []
        if entry.original_path:
            meta.append(self._shorten_path(entry.original_path))
        if entry.deleted_at:
            meta.append(entry.deleted_at.strftime("%Y-%m-%d %H:%M"))
        if entry.size is not None:
            meta.append(
                natural_size(
                    entry.size,
                    config["metadata"]["filesize_suffix"],
                    config["metadata"]["filesize_decimals"],
                )
            )
        if meta:
            prompt.append(f"  {' · '.join(meta)}", style="dim")
        return prompt

    @work(thread=True)
    def reload_entries(self) -> None:
        selection_list = self.query_one("#trash_entries", TrashSelectionList)

        # Remember the current highlight (by stable handle, then index) and
        # scroll position so a reload after an operation is not jarring.
        prev_handle: str | None = None
        prev_index = selection_list.highlighted
        if prev_index is not None and 0 <= prev_index < selection_list.option_count:
            prev_handle = selection_list.get_option_at_index(prev_index).value
        prev_scroll = selection_list.scroll_offset.y

        self.entries = self.recycle_bin.entries()
        self._by_handle = {
            self._handle_of(entry, index): entry
            for index, entry in enumerate(self.entries)
        }
        self.app.call_from_thread(
            selection_list.set_options,
            [
                Selection(self._format_entry(entry), self._handle_of(entry, index))
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

        self.query_one(
            "#dialog"
        ).border_subtitle = (
            f"{len(self.entries)} item{'s' if len(self.entries) != 1 else ''}"
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
