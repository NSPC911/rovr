import asyncio
from typing import ClassVar

from rich.segment import Segment
from rich.style import Style
from textual import events, work
from textual.binding import BindingType
from textual.content import Content
from textual.strip import Strip
from textual.widgets import Button, SelectionList
from textual.widgets.option_list import OptionDoesNotExist

from rovr.classes import ClipboardSelection
from rovr.functions import icons as icon_utils
from rovr.variables.constants import config, vindings


class Clipboard(SelectionList, inherit_bindings=False):
    """A selection list that displays the clipboard contents."""

    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.clipboard_contents = []

    def on_mount(self) -> None:
        self.paste_button: Button = self.app.query_one("#paste")
        self.paste_button.disabled = True
        self.file_list = self.app.query_one("#file_list")

    @work
    async def copy_to_clipboard(self, items: list[str]) -> None:
        """Copy the selected files to the clipboard"""
        self.deselect_all()
        await asyncio.sleep(0)
        for item in items[::-1]:
            self.insert_selection_at_beginning(
                ClipboardSelection(
                    prompt=Content(
                        f"{icon_utils.get_icon('general', 'copy')[0]} {item}"
                    ),
                    text=item,
                    type_of_selection="copy",
                )
            )
        self.paste_button.disabled = False
        for item_number in range(len(items)):
            self.select(self.get_option_at_index(item_number))

    @work
    async def cut_to_clipboard(self, items: list[str]) -> None:
        self.deselect_all()
        await asyncio.sleep(0)
        """Cut the selected files to the clipboard."""
        for item in items[::-1]:
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
        self.paste_button.disabled = False
        for item_number in range(len(items)):
            self.select(self.get_option_at_index(item_number))

    # Use better versions of the checkbox icons
    def _get_left_gutter_width(
        self,
    ) -> int:
        """Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
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
        line = super(SelectionList, self).render_line(y)

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

    # Why isnt this already a thing
    def insert_selection_at_beginning(self, content: ClipboardSelection) -> None:
        """Insert a new selection at the beginning of the clipboard list.

        Args:
            content (ClipboardSelection): A pre-created Selection object to insert.
        """
        # Check for duplicate ID
        if content.id is not None and content.id in self._id_to_option:
            self.remove_option(content.id)

        # insert
        self._options.insert(0, content)

        # update self._values
        values = {content.value: 0}

        # update mapping
        for option, index in list(self._option_to_index.items()):
            self._option_to_index[option] = index + 1
        for key, value in self._values.items():
            values[key] = value + 1
        self._values = values
        self._option_to_index[content] = 0

        # update id mapping
        if content.id is not None:
            self._id_to_option[content.id] = content

        # force redraw
        self._clear_caches()

        # since you insert at beginning, highlighted should go down
        if self.highlighted is not None:
            self.highlighted += 1

        # redraw
        # self.refresh(layout=True)

    @work
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
                self.remove_option_at_index(self.highlighted)
                self.paste_button.disabled = self.add_options
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
