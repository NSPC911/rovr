from copy import copy
from os import path
from typing import Any, ClassVar, Literal, cast

from textual import events, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.reactive import reactive
from textual.widgets import Button, ListItem, ListView, Static
from textual.worker import Worker

from rovr.classes.type_aliases import CallableNone
from rovr.functions import icons as icon_utils
from rovr.functions.path import control, normalise
from rovr.functions.utils import s
from rovr.variables.constants import bindings, config


def _clipboard_icon(icon: str) -> str:
    get_icon = icon_utils.get_toggle_button_icon
    return get_icon("left") + icon + get_icon("right")


class ClipboardSelectionMark(Static):
    ALLOW_SELECT = False
    selected: reactive[bool] = reactive(False)

    def __init__(self, item: str, operation_icon: str | None = None) -> None:
        super().__init__(classes="clipboard-path", markup=False)
        self.item = control(item)
        self.operation_icon = operation_icon

    def render(self) -> str:
        get_icon = icon_utils.get_toggle_button_icon
        inner = get_icon("inner_filled" if self.selected else "inner")
        indicator = _clipboard_icon(inner)
        if self.operation_icon is not None:
            indicator += f" {self.operation_icon}"
        return f"{indicator} {self.item}"


class ClipboardBlock(ListItem):
    active: reactive[bool] = reactive(False)

    def __init__(
        self, paths: tuple[str, ...], type_of_selection: Literal["copy", "cut"]
    ) -> None:
        super().__init__(id=f"clipboard-block-{id(self)}")
        self.paths: tuple[str, ...] = paths
        self.type_of_selection: Literal["copy", "cut"] = type_of_selection

    def compose(self) -> ComposeResult:
        icon = icon_utils.get_icon("general", self.type_of_selection)[0]
        yield ClipboardSelectionMark(
            self.paths[0], operation_icon=icon if len(self.paths) == 1 else None
        ).data_bind(selected=ClipboardBlock.active)
        for index, item in enumerate(self.paths[1:4], 1):
            prefix = _clipboard_icon(icon if index == 1 else " ")
            yield Static(
                f"{prefix} {control(item)}", markup=False, classes="clipboard-path"
            )
        if len(self.paths) > 4:
            yield Static(
                f"{_clipboard_icon(' ')} ... and {len(self.paths) - 4} more item{s(len(self.paths) - 4)}",
                classes="clipboard-path clipboard-more",
            )

    def _on_click(self, event: events.Click) -> None:  # ty: ignore[invalid-method-override]
        event.prevent_default()
        if event.button != 1:
            return

        list_view = self.parent
        assert isinstance(list_view, ListView)
        list_view.focus()
        list_view.index = list_view.children.index(self)
        if event.chain == 2:
            self.post_message(self._ChildClicked(self))


class Clipboard(ListView, inherit_bindings=False):
    """A list of file operation blocks stored in the clipboard."""

    key_contexts = ("clipboard", "lists")

    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(initial_index=None, id="clipboard")
        self._checker_worker: Worker | None = None
        self._dimmed_update_pending = False
        self._active: ClipboardBlock | None = None

    def on_mount(self) -> None:
        self.paste_button: Button = self.app.query_one("#paste", Button)
        self.paste_button.disabled = True
        self.set_interval(
            5, self.checker_wrapper, name="Check existence of clipboard items"
        )

    def on_focus(self) -> None:
        if self.children and (
            self.highlighted_child is None or not self.highlighted_child.highlighted
        ):
            self.index = (
                self.children.index(self._active)
                if self._active in self.children
                else (self.index or 0)
            )

    @property
    def options(self) -> tuple[ClipboardBlock, ...]:
        return cast(tuple[ClipboardBlock, ...], self.children)

    @property
    def selected(self) -> tuple[Literal["copy", "cut"] | None, list[str]]:
        if self._active is None:
            return None, []
        return self._active.type_of_selection, list(self._active.paths)

    def is_cut(self, item: str) -> bool:
        return (
            self._active is not None
            and self._active.type_of_selection == "cut"
            and normalise(item) in self._active.paths
        )

    @work
    async def copy_to_clipboard(self, items: list[str], select: bool = True) -> None:
        await self._add_block(items, "copy", select)

    @work
    async def cut_to_clipboard(self, items: list[str], select: bool = True) -> None:
        await self._add_block(items, "cut", select)

    async def _add_block(
        self,
        items: list[str],
        operation: Literal["copy", "cut"],
        select: bool,
    ) -> None:
        async with self.batch():
            paths = tuple(dict.fromkeys(items))
            if not paths:
                return

            highlighted = self.highlighted_child
            # prevents double highlights
            if highlighted is not None:
                self.index = None
            old = next((block for block in self.options if block.paths == paths), None)
            activate = select or (old is self._active and old is not None)
            if old is not None:
                if old is self._active:
                    self._set_active(None)
                await old.remove()

            block = ClipboardBlock(paths, operation)
            await self.insert(0, [block])
            if activate and self.children and self.children[0] is block:
                self.set_index(0)
            elif highlighted in self.children:
                self.index = self.children.index(highlighted)
            self._clipboard_changed()

    def _set_active(self, block: ClipboardBlock | None) -> None:
        if self._active is block:
            return
        if self._active is not None:
            self._active.active = False
        self._active = block
        if block is not None:
            block.active = True
        self.paste_button.disabled = block is None
        self._clipboard_changed()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        assert isinstance(event.item, ClipboardBlock)
        self._set_active(event.item)

    def action_select(self) -> None:
        block = self.highlighted_child
        if isinstance(block, ClipboardBlock):
            self._set_active(block)

    def action_cursor(self, offset: int) -> None:
        action: CallableNone = (
            self.action_cursor_down if offset > 0 else self.action_cursor_up
        )
        for _ in range(abs(offset)):
            action()

    def action_cursor_page(self, pages: float) -> None:
        [
            (self.action_page_down if pages > 0 else self.action_page_up)()
            for _ in range(abs(int(pages)))
        ]

    def action_first(self) -> None:
        if self.children:
            self.index = 0

    def action_last(self) -> None:
        if self.children:
            self.index = len(self.children) - 1

    async def on_key(self, event: events.Key) -> None:
        if self.has_focus and event.key in config.get("keybinds", {}).get("delete", []):
            await self.action_delete()
            event.stop()

    def _queue_dimmed_update(self) -> None:
        if not self._dimmed_update_pending:
            self._dimmed_update_pending = True
            self.call_after_refresh(self._update_dimmed_items)

    def _update_dimmed_items(self) -> None:
        self._dimmed_update_pending = False
        cast(Any, self.app).file_list.update_dimmed_items()

    @work(thread=True)
    def check_clipboard_existence(self) -> None:
        """Remove paths from the clipboard that no longer exist."""
        blocks = copy(self.options)
        existing = {
            block.id: tuple(item for item in block.paths if path.lexists(item))
            for block in blocks
        }
        if any(existing[block.id] != block.paths for block in blocks):
            self.app.call_from_thread(self._remove_missing_paths, existing)

    async def _remove_missing_paths(
        self, existing: dict[str | None, tuple[str, ...]]
    ) -> None:
        changed = False
        for block in list(self.options):
            paths = existing.get(block.id, block.paths)
            if paths == block.paths:
                continue
            changed = True
            if paths:
                block.paths = paths
                block.refresh(recompose=True)
            else:
                if block is self._active:
                    self._set_active(None)
                await block.remove()
        if changed:
            self._clipboard_changed()

    def checker_wrapper(self) -> None:
        if self._checker_worker is None or not self._checker_worker.is_running:
            self._checker_worker = self.check_clipboard_existence()

    async def action_delete(self) -> None:
        block = self.highlighted_child
        if not isinstance(block, ClipboardBlock):
            self.notify(
                "No block selected to delete from the clipboard.",
                title="Clipboard",
                severity="warning",
            )
            return
        await self.remove_block(self.options.index(block))

    async def remove_block(self, index: int) -> None:
        block = self.options[index]
        if block is self._active:
            self._set_active(None)
        await self.pop(index)
        self._clipboard_changed()

    def _clipboard_changed(self) -> None:
        self._queue_dimmed_update()
        cast(Any, self.app).update_terminal_title()

    def set_index(self, index: int | None) -> None:
        self.index = None
        self._set_active(None if index is None else self.options[index])
        self.index = index
