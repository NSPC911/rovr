from __future__ import annotations

from typing import Iterable

from rich.segment import Segment
from textual import _border as border
from textual.content import Content
from textual.css.types import EdgeType
from textual.style import Style
from textual.widgets import Input


def render_border_label(
    label: tuple[Content, Style],
    is_title: bool,
    name: EdgeType,
    width: int,
    inner_style: Style,
    outer_style: Style,
    style: Style,
    has_left_corner: bool,
    has_right_corner: bool,
) -> Iterable[Segment]:
    """Render a border label (the title or subtitle) with optional markup.

    The styling that may be embedded in the label will be reapplied after taking into
    account the inner, outer, and border-specific, styles.

    Args:
        label: Tuple of label and style to render in the border.
        is_title: Whether we are rendering the title (`True`) or the subtitle (`False`).
        name: Name of the box type.
        width: The width, in cells, of the space available for the whole edge.
            This is the total space that may also be needed for the border corners and
            the whitespace padding around the (sub)title. Thus, the effective space
            available for the border label is:
            - `width` if no corner is needed;
            - `width - 2` if one corner is needed; and
            - `width - 4` if both corners are needed.
        inner_style: The inner style (widget background).
        outer_style: The outer style (parent background).
        style: Widget style.
        has_left_corner: Whether the border edge will have to render a left corner.
        has_right_corner: Whether the border edge will have to render a right corner.

    Yields:
        A list of segments that represent the full label and surrounding padding.
    """
    # How many cells do we need to reserve for surrounding blanks and corners?
    corners_needed = has_left_corner + has_right_corner
    cells_reserved = 2 * corners_needed

    text_label, label_style = label

    if not text_label.cell_length or width <= cells_reserved:
        return

    text_label = text_label.truncate(width - cells_reserved, ellipsis=True)
    # if has_left_corner:
    #     text_label = text_label.pad_left(1)
    # if has_right_corner:
    #     text_label = text_label.pad_right(1)
    text_label = text_label.pad(1, 1)

    text_label = text_label.stylize_before(label_style)

    label_style_location = border.BORDER_LABEL_LOCATIONS[name][0 if is_title else 1]
    flip_top, flip_bottom = border.BORDER_TITLE_FLIP.get(name, (False, False))

    inner = inner_style + style
    outer = outer_style + style

    base_style: Style
    if label_style_location == 0:
        base_style = inner
    elif label_style_location == 1:
        base_style = outer
    elif label_style_location == 2:
        base_style = Style(outer.background, inner.foreground, reverse=True)
    elif label_style_location == 3:
        base_style = Style(inner.background, outer.foreground, reverse=True)
    else:
        assert False

    if (flip_top and is_title) or (flip_bottom and not is_title):
        base_style = base_style.without_color + Style(
            background=base_style.foreground,
            foreground=base_style.background,
        )

    segments = text_label.render_segments(base_style)
    yield from segments


border.render_border_label = render_border_label  # ty: ignore

# make it less bold
border.BORDER_CHARS["dashed"] = (
    ("┌", "╌", "┐"),
    ("┆", " ", "┆"),
    ("└", "╌", "┘"),
)

# with the current implementation it just checks if the character is printable
# problem is that kitty kp sends ctrl+a as a, which is printable, but we don't want
# to consume it, so we need to check if the key is just that key
Input.check_consume_key = lambda self, key, character: (  # ty: ignore[invalid-assignment]
    character
    and len(character) == 1
    and not key.startswith(("ctrl", "shift", "alt", "super"))
    and character.isprintable()
)
