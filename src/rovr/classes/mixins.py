from rich.segment import Segment
from rich.style import Style
from textual.geometry import Size
from textual.strip import Strip
from textual.widgets import OptionList
from textual.widgets.option_list import OptionDoesNotExist

from rovr.functions import icons as icon_utils


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
    def _get_left_gutter_width(self) -> int:
        """
        Returns the size of any left gutter that should be taken into account.

        Returns:
            The width of the left gutter.
        """
        if (
            hasattr(self, "dummy")
            and self.dummy
            or (hasattr(self, "select_mode_enabled") and not self.select_mode_enabled)
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
        component_class = ""
        if selection_style == "selection-list--button-selected":
            component_class = selection_style
        elif option.disabled:
            component_class = "option-list--option-disabled"
        elif self.highlighted == option_index:
            component_class = "option-list--option-highlighted"
        elif mouse_over:
            component_class = "option-list--option-hover"

        if component_class:
            style = self.get_visual_style("option-list--option", component_class)
        else:
            style = self.get_visual_style("option-list--option")

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
        if (hasattr(self, "dummy") and self.dummy) or (
            hasattr(self, "select_mode_enabled") and not self.select_mode_enabled
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

        # Determine checkbox style
        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        line = self.super_render_line(y, component_style)
        underlying_style = next(iter(line)).style or self.rich_style
        assert underlying_style is not None

        button_style = self.get_component_rich_style(component_style)

        side_style = Style.from_color(button_style.bgcolor, underlying_style.bgcolor)

        side_style += Style(meta={"option": selection_index})
        button_style += Style(meta={"option": selection_index})

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
