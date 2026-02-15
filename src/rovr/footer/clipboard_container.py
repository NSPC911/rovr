import asyncio
from os import path
from typing import ClassVar, Self, Sequence

from textual import events, work
from textual.binding import BindingType
from textual.content import Content
from textual.widgets import Button, SelectionList
from textual.widgets.option_list import OptionDoesNotExist
from textual.worker import Worker

from rovr.classes.mixins import CheckboxRenderingMixin
from rovr.classes.textual_options import ClipboardSelection, ClipboardSelectionValue
from rovr.functions import icons as icon_utils
from rovr.functions.path import dump_exc
from rovr.variables.constants import config, vindings


class Clipboard(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    """A selection list that displays the clipboard contents."""

    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.clipboard_contents = []
        self._checker_worker: Worker | None = None
        self._options: list[ClipboardSelection] = []

    def on_mount(self) -> None:
        self.paste_button: Button = self.app.query_one("#paste")
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
    async def copy_to_clipboard(self, items: list[str]) -> None:
        """Copy the selected files to the clipboard"""
        self.deselect_all()
        for item in items[::-1]:
            await asyncio.sleep(0)
            self.insert_selection_at_beginning(
                ClipboardSelection(
                    prompt=Content(
                        f"{icon_utils.get_icon('general', 'copy')[0]} {item}"
                    ),
                    text=item,
                    type_of_selection="copy",
                )
            )
        for item_number in range(len(items)):
            self.select(self.get_option_at_index(item_number))
        # then go through filelist and dim the cut items

    @work
    async def cut_to_clipboard(self, items: list[str]) -> None:
        """Cut the selected files to the clipboard."""
        self.deselect_all()
        for item in items[::-1]:
            await asyncio.sleep(0)
            if isinstance(item, str):
                self.insert_selection_at_beginning(
                    ClipboardSelection(
                        prompt=Content(
                            f"{icon_utils.get_icon('general', 'cut')[0]} {item}"
                        ),
                        text=item,
                        type_of_selection="cut",
                    )
                )
        for item_number in range(len(items)):
            self.select(self.get_option_at_index(item_number))

    # Why isnt this already a thing
    def insert_selection_at_beginning(self, selection: ClipboardSelection) -> None:
        """Insert a new selection at the beginning of the clipboard list.

        Args:
            selection (ClipboardSelection): A pre-created Selection object to insert.
        """
        # Check for duplicate ID
        if selection.id is not None and selection.id in self._id_to_option:
            self.remove_option(selection.id)
        # check for duplicate path
        if any(selection.value.path == option.value.path for option in self.options):
            # find the option with the same path
            for option in self.options:
                if selection.value.path == option.value.path:
                    self._remove_option(option)
                    break

        # insert
        self._options.insert(0, selection)

        values = {selection.value: 0}

        # update mapping
        for option, index in list(self._option_to_index.items()):
            self._option_to_index[option] = index + 1
        for key, value in self._values.items():
            values[key] = value + 1
        self._values = values
        self._option_to_index[selection] = 0

        if selection.id is not None:
            self._id_to_option[selection.id] = selection

        # force redraw
        self._clear_caches()
        self._update_lines()

        # since you insert at beginning, highlighted should go down
        if self.highlighted is not None:
            self.highlighted += 1

        # redraw because may not work, but idk honestly, just a preventive measure again
        self.refresh(layout=True)

    async def on_key(self, event: events.Key) -> None:
        if self.has_focus:
            if event.key in config["keybinds"]["delete"]:
                """Delete the selected files from the clipboard."""
                if self.highlighted is None:
                    self.notify(
                        "No files selected to delete from the clipboard.",
                        title="Clipboard",
                        severity="warning",
                    )
                    return
                try:
                    self.remove_option_at_index(self.highlighted)
                except (KeyError, OptionDoesNotExist) as exc:
                    dump_exc(self, exc)
                if self.option_count == 0:
                    return
                event.stop()
            elif event.key in config["keybinds"]["toggle_all"]:
                """Select all items in the clipboard."""
                if len(self.selected) == len(self.options):
                    self.deselect_all()
                else:
                    self.select_all()
                event.stop()

    def _remove_option(self, option: ClipboardSelection) -> Self:  # ty: ignore[invalid-method-override]  # oh my god, will you please stfu
        super()._remove_option(option)
        self.app.file_list.update_dimmed_items([
            opt.value.path
            for opt in self.options
            if opt.value in self.selected and opt.value.type_of_selection == "cut"
        ])
        return self

    async def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        self.paste_button.disabled = len(self.selected) == 0
        # go through each option, check if they are both selected and are the cut type, update filelist with that list
        self.app.file_list.update_dimmed_items([
            option.value.path
            for option in self.options
            if option.value in self.selected and option.value.type_of_selection == "cut"
        ])

    @work(thread=True)
    def check_clipboard_existence(self) -> None:
        """Check if the files in the clipboard still exist."""
        for option in self.options:
            if not path.exists(option.value.path):
                assert isinstance(option.id, str)
                self.call_later(self.remove_option, option.id)

    def checker_wrapper(self) -> None:
        if self._checker_worker is None or not self._checker_worker.is_running:
            self._checker_worker: Worker = self.check_clipboard_existence()
