from inspect import isawaitable
from typing import Any, Awaitable, Callable, Iterable, NamedTuple, Self

from rich.segment import Segment
from rich.style import Style
from textual.content import ContentText
from textual.events import Key
from textual.geometry import Region, Size
from textual.strip import Strip
from textual.widgets import OptionList
from textual.widgets.option_list import Option, OptionDoesNotExist
from textual.widgets.selection_list import Selection, SelectionType

from rovr.classes.textual_options import LazySelection
from rovr.functions import icons as icon_utils
from rovr.functions.utils import check_key
from rovr.variables.constants import (
    config,
)


class SingleLineOptionLayoutMixin:
    """OptionList/SelectionList layout optimization for single-line rows."""

    def _update_lines(self) -> None:
        """Update line caches without forcing prompt visualization for all options."""
        if not self.scrollable_content_region:
            return

        line_cache = self._line_cache
        lines = line_cache.lines
        next_index = lines[-1][0] + 1 if lines else 0

        if next_index < len(self.options):
            for index, option in enumerate(self.options[next_index:], next_index):
                line_cache.index_to_line[index] = len(line_cache.lines)
                line_count = 1 + int(option._divider)
                line_cache.heights[index] = line_count
                line_cache.lines.extend(
                    (index, line_no) for line_no in range(line_count)
                )

        last_divider = self.options and self.options[-1]._divider
        width = self.scrollable_content_region.width - self._get_left_gutter_width()
        virtual_size = Size(width, len(lines) - (1 if last_divider else 0))
        if virtual_size != self.virtual_size:
            self.virtual_size = virtual_size
            self._scroll_update(virtual_size)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        del viewport
        return container.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        del container, viewport, width
        last_divider = self.options and self.options[-1]._divider
        return sum(1 + int(option._divider) for option in self.options) - (
            1 if last_divider else 0
        )


class CheckboxRenderingMixin:
    def _get_option_component_classes(self, option: Option) -> list[str]:
        if hasattr(option, "get_component_classes") and callable(
            option.get_component_classes
        ):
            return list(option.get_component_classes())  # ty: ignore
        return []

    def _get_left_gutter_width(self) -> int:
        """
        Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
        if getattr(self, "dummy", False) or not getattr(
            self, "select_mode_enabled", True
        ):
            return 0

        icons = [
            icon_utils.get_toggle_button_icon("left"),
            icon_utils.get_toggle_button_icon("inner"),
            icon_utils.get_toggle_button_icon("right"),
            " ",
        ]

        return len("".join(icons))

    def super_render_line(self, y: int, selection_style: str = "") -> Strip:
        base_line = OptionList.render_line(self, y)  # ty: ignore[invalid-argument-type]

        line_number = self.scroll_offset.y + y
        try:
            option_index, line_offset = self._lines[line_number]
            option = self.options[option_index]
        except (IndexError, AttributeError):
            return base_line

        mouse_over: bool = self._mouse_hovering_over == option_index
        option_component_classes = self._get_option_component_classes(option)

        if selection_style == "selection-list--button-selected":
            option_component_classes.insert(0, selection_style)
        elif option.disabled:
            option_component_classes.insert(0, "option-list--option-disabled")
        elif self.highlighted == option_index:
            option_component_classes = ["option-list--option-highlighted"] + [
                f"{part}--highlighted" for part in option_component_classes
            ]
        elif mouse_over:
            option_component_classes = ["option-list--option-hover"] + [
                f"{part}--hovered" for part in option_component_classes
            ]

        style = self.get_visual_style("option-list--option", *option_component_classes)

        strips = self._get_option_render(option, style)
        try:
            strip = strips[line_offset]
        except IndexError:
            return base_line
        return strip

    def render_line(self, y: int) -> Strip:
        """
        Render a line in the display with optional checkbox rendering.

        Args:
            y: The line to render.

        Returns:
            A Strip that is the line to render.
        """
        # Check if we should render checkboxes
        if getattr(self, "dummy", False) or not getattr(
            self, "select_mode_enabled", True
        ):
            return self.super_render_line(y)

        # Base line rendering
        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return Strip([*self.super_render_line(y)])

        if selection.disabled:
            return Strip([*self.super_render_line(y)])

        line = self.super_render_line(y)
        underlying_style = next(iter(line)).style or self.rich_style
        assert underlying_style is not None

        side_style = underlying_style + Style(meta={"option": selection_index})
        button_style = underlying_style + Style(meta={"option": selection_index})

        # Get checkbox icons
        icons = [
            icon_utils.get_toggle_button_icon("left"),
            icon_utils.get_toggle_button_icon("inner"),
            icon_utils.get_toggle_button_icon("right"),
            " ",
        ]

        return Strip([
            Segment(icons[0], style=side_style),
            Segment(
                icon_utils.get_toggle_button_icon("inner_filled")
                if selection.value in self._selected
                else icons[1],
                style=button_style,
            ),
            Segment(icons[2], style=side_style),
            Segment(icons[3], style=underlying_style),
            *line,
        ])

    def render_lines(self, crop: Region) -> list[Strip]:
        try:
            return super(OptionList, self).render_lines(crop)  # ty: ignore[invalid-super-argument]
        except KeyError:
            return []


class ScrollOffMixin:
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


class Action(NamedTuple):
    action: str | Callable[[], Any]
    match_keys: str | list[str]
    only_if: bool | Callable[[], bool] = True


class Actionable:
    ACTIONS: list[Action]

    async def on_key(self, event: Key) -> None:
        try:
            iter(self.ACTIONS)
        except AttributeError:
            return

        for action in self.ACTIONS:
            if check_key(event, action.match_keys) and (
                action.only_if() if callable(action.only_if) else action.only_if
            ):
                if not isinstance(action.action, str):
                    func: Callable[[], Any] = action.action
                else:
                    func: Callable[[], Any] | None = getattr(
                        self, f"action_{action.action}"
                    )
                    if not callable(func):
                        continue
                result: Any | Awaitable = func()
                if isawaitable(result):
                    await result
                if getattr(self.app, "_show_keys", False):
                    self.app.show_key(event)
                event.prevent_default().stop()
                return


class SetOptionsSelectionList:
    def set_options(
        self,
        options: Iterable[
            Selection[SelectionType]
            | LazySelection[SelectionType]
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
