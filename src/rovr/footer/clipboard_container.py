from os import path
from typing import ClassVar, Literal, Self, Sequence

from textual import events, work
from textual.binding import BindingType
from textual.widgets import Button, SelectionList
from textual.widgets.option_list import OptionDoesNotExist
from textual.worker import Worker

from rovr.classes.mixins import (
    CheckboxRenderingMixin,
    SelectionNavigationMixin,
    SetOptionsSelectionList,
)
from rovr.classes.textual_options import ClipboardSelection, ClipboardSelectionValue
from rovr.functions import icons as icon_utils
from rovr.functions.utils import dump_on_exc
from rovr.variables.constants import bindings, config


class Clipboard(
    CheckboxRenderingMixin,
    SelectionNavigationMixin,
    SetOptionsSelectionList,
    SelectionList,
    inherit_bindings=False,
):
    """A selection list that displays the clipboard contents."""

    key_contexts = ("clipboard", "lists")

    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(id="clipboard")
        self.clipboard_contents = []
        self._checker_worker: Worker | None = None
        self._dimmed_update_pending = False
        self._options: list[ClipboardSelection] = []

    def on_mount(self) -> None:
        self.paste_button: Button = self.app.query_one("#paste", Button)
        self.paste_button.disabled = True
        self.set_interval(
            5, self.checker_wrapper, name="Check existence of clipboard items"
        )

    @property
    def options(self) -> Sequence[ClipboardSelection]:
        """Sequence of options in the OptionList.

        !!! note "This is read-only"

        """
        return self._options

    @property
    def selected(self) -> list[ClipboardSelectionValue]:
        """The selected values.

        This is a list of all of the
        [values][textual.widgets.selection_list.Selection.value] associated
        with selections in the list that are currently in the selected
        state.
        """
        return list(self._selected.keys())

    @work
    async def copy_to_clipboard(
        self, items: list[str], select: Literal["reselect", "select", "no"] = "reselect"
    ) -> None:
        """Copy the selected files to the clipboard"""
        items = list(dict.fromkeys(items))
        self._prepend_selections(
            [
                ClipboardSelection(
                    prompt=f"{icon_utils.get_icon('general', 'copy')[0]} {item}",
                    text=item,
                    type_of_selection="copy",
                )
                for item in items
            ],
            select,
        )

    @work
    async def cut_to_clipboard(
        self, items: list[str], select: Literal["reselect", "select", "no"] = "reselect"
    ) -> None:
        """Cut the selected files to the clipboard."""
        items = list(dict.fromkeys(items))
        self._prepend_selections(
            [
                ClipboardSelection(
                    prompt=f"{icon_utils.get_icon('general', 'cut')[0]} {item}",
                    text=item,
                    type_of_selection="cut",
                )
                for item in items
            ],
            select,
        )

    # Why isnt this already a thing
    def insert_selection_at_beginning(self, selection: ClipboardSelection) -> None:
        """Insert a new selection at the beginning of the clipboard list.

        Args:
            selection (ClipboardSelection): A pre-created Selection object to insert.
        """
        self._prepend_selections([selection], "no")

    def _prepend_selections(
        self,
        selections: list[ClipboardSelection],
        select: Literal["reselect", "select", "no"],
    ) -> None:
        paths = {option.value.path for option in selections}
        remaining = [option for option in self.options if option.value.path not in paths]
        selected = set(self.selected) if select != "reselect" else set()
        highlighted = self.highlighted_option
        highlighted_path = highlighted.value.path if highlighted is not None else None
        options = selections + remaining
        with self.prevent(SelectionList.SelectedChanged):
            self.set_options(options)
            for index, option in enumerate(options):
                if (index < len(selections) and select != "no") or (
                    index >= len(selections) and option.value in selected
                ):
                    self.select(option)
                if option.value.path == highlighted_path:
                    self.highlighted = index
        self._message_changed()

    async def on_key(self, event: events.Key) -> None:
        if self.has_focus:
            if event.key in config["keybinds"]["delete"]:
                self.action_delete()
                event.stop()
            elif event.key in config["keybinds"]["toggle_all"]:
                self.action_toggle_all()
                event.stop()

    def _remove_option(self, option: ClipboardSelection) -> Self:  # ty: ignore[invalid-method-override]  # oh my god, will you please stfu
        super()._remove_option(option)
        self._queue_dimmed_update()
        return self

    def _queue_dimmed_update(self) -> None:
        if not self._dimmed_update_pending:
            self._dimmed_update_pending = True
            self.call_after_refresh(self._update_dimmed_items)

    def _update_dimmed_items(self) -> None:
        self._dimmed_update_pending = False
        self.app.file_list.update_dimmed_items()

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        self.paste_button.disabled = len(self.selected) == 0
        self._queue_dimmed_update()
        self.app.update_terminal_title()

    def safe_remove_option(self, option_id: str) -> None:
        """Safely remove an option by its ID, handling exceptions."""
        try:
            self.remove_option(option_id)
        except (KeyError, OptionDoesNotExist):
            return

    @work(thread=True)
    def check_clipboard_existence(self) -> None:
        """Check if the files in the clipboard still exist."""
        missing = []
        for option in list(self.options):
            if not path.lexists(option.value.path):
                assert isinstance(option.id, str)
                missing.append(option.id)
        if missing:
            self.app.call_from_thread(self._remove_missing_options, missing)

    def _remove_missing_options(self, option_ids: list[str]) -> None:
        for option_id in option_ids:
            self.safe_remove_option(option_id)

    def checker_wrapper(self) -> None:
        if self._checker_worker is None or not self._checker_worker.is_running:
            self._checker_worker: Worker = self.check_clipboard_existence()

    def action_delete(self) -> None:
        """Delete the selected files from the clipboard."""
        if self.highlighted is None:
            self.notify(
                "No files selected to delete from the clipboard.",
                title="Clipboard",
                severity="warning",
            )
            return
        with dump_on_exc(self, KeyError, OptionDoesNotExist):
            self.remove_option_at_index(self.highlighted)

    def action_toggle_all(self) -> None:
        """Select all items in the clipboard."""
        if len(self.selected) == len(self.options):
            self.deselect_all()
        else:
            self.select_all()
