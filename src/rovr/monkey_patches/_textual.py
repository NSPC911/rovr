from __future__ import annotations

from functools import lru_cache
from typing import IO, Iterable, cast

from PIL import Image as PILImage
from rich.ansi import AnsiDecoder
from rich.color import Color
from rich.color_triplet import ColorTriplet
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style as RStyle
from rich.text import Text
from textual import _border as border
from textual import events
from textual._compositor import Compositor
from textual._xterm_parser import (
    FUNCTIONAL_KEYS,
    MODIFIER_FUNCTIONAL_KEYS,
    SPECIAL_KEY_TO_CHARACTER,
    XTermParser,
    _re_extended_key,
)
from textual.content import Content
from textual.css.types import EdgeType
from textual.geometry import Region, Size
from textual.keys import _character_to_key
from textual.map_geometry import MapGeometry
from textual.scrollbar import ScrollBar
from textual.style import Style as TStyle
from textual.widget import Widget
from textual.widgets import Input
from textual_image import _pixeldata
from textual_image._geometry import ImageSize
from textual_image._terminal import get_cell_size
from textual_image._utils import StrOrBytesPath, grouped
from textual_image.renderable import halfcell

from rovr.variables.constants import RESAMPLING_METHOD

# ---------------------------- textual-image monkey patches -----------------------------


def scaled(self: _pixeldata.PixelData, width: int, height: int) -> _pixeldata.PixelData:
    scaled_image = self._image.resize((width, height), resample=RESAMPLING_METHOD())
    return _pixeldata.PixelData(scaled_image)


_pixeldata.PixelData.scaled = scaled  # ty: ignore[invalid-assignment]


def _map_pixel(pixel: tuple[int, int, int, int]) -> Color:
    return Color.from_triplet(ColorTriplet(*pixel[:3]))


def halfcell_init(
    self: halfcell.Image,
    image: StrOrBytesPath | IO[bytes] | PILImage.Image,
    width: int | str | None = None,
    height: int | str | None = None,
) -> None:
    image_data = _pixeldata.PixelData(image)
    self._image_data = _pixeldata.PixelData(image_data.pil_image.convert("RGBA"))
    self._render_size = ImageSize(
        self._image_data.width, self._image_data.height, width, height
    )


def halfcell_rich_console(
    self: halfcell.Image, console: Console, options: ConsoleOptions
) -> RenderResult:
    terminal_sizes = get_cell_size()
    width, height = self._render_size.get_cell_size(
        options.max_width, options.max_height, terminal_sizes
    )

    for upper_row, lower_row in grouped(self._image_data.scaled(width, height * 2), 2):
        for upper_pixel, lower_pixel in zip(upper_row, lower_row, strict=True):
            upper = cast(tuple[int, int, int, int], upper_pixel)
            lower = cast(tuple[int, int, int, int], lower_pixel)
            if upper[3] == lower[3] == 0:
                yield Segment(" ")
            elif upper[3] == 0:
                yield Segment("▄", style=RStyle(color=_map_pixel(lower)))
            elif lower[3] == 0:
                yield Segment("▀", style=RStyle(color=_map_pixel(upper)))
            else:
                yield Segment(
                    "▀",
                    style=RStyle(color=_map_pixel(upper), bgcolor=_map_pixel(lower)),
                )
        yield Segment("\n")


halfcell.Image.__init__ = halfcell_init  # ty: ignore[invalid-assignment]
halfcell.Image.__rich_console__ = halfcell_rich_console  # ty: ignore[invalid-assignment]


# -------------------------------- rich monkey patches ----------------------------------


# https://github.com/Textualize/rich/issues/4090
def decode(self: AnsiDecoder, terminal_text: str) -> Iterable[Text]:
    for line in terminal_text.splitlines():
        yield self.decode_line(line)


AnsiDecoder.decode = decode  # ty: ignore[invalid-assignment]

_render_border_label = border.render_border_label

# ------------------------------- textual monkey patches --------------------------------


def render_border_label(
    label: tuple[Content, TStyle],
    is_title: bool,
    name: EdgeType,
    width: int,
    inner_style: TStyle,
    outer_style: TStyle,
    style: TStyle,
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
    label = (label[0].pad(1, 1), label[1])
    yield from _render_border_label(
        label, is_title, name, width, inner_style, outer_style, style, False, False
    )


border.render_border_label = render_border_label  # ty: ignore

# make it less bold
border.BORDER_CHARS["dashed"] = (
    ("┌", "╌", "┐"),
    ("┆", " ", "┆"),
    ("└", "╌", "┘"),
)


_arrange_scrollbars = Widget._arrange_scrollbars


def arrange_scrollbars(self: Widget, region: Region) -> Iterable[tuple[Widget, Region]]:
    scrollbars = list(_arrange_scrollbars(self, region))
    parent = self.parent
    # fun fact: setting border: none still provides  ("", Color(0,0,0,255))
    # as a border, so theres no point in checking for none
    border_bottom = bool(
        self.styles.border_bottom[0]
        or isinstance(parent, Widget)
        and parent.styles.border_bottom[0]
    )
    border_right = bool(
        self.styles.border_right[0]
        or isinstance(parent, Widget)
        and parent.styles.border_right[0]
    )
    both_on_border = border_bottom and border_right and len(scrollbars) == 3

    for scrollbar, scrollbar_region in scrollbars:
        if both_on_border and not hasattr(scrollbar, "vertical"):
            continue
        if getattr(scrollbar, "vertical", False) and border_right:
            scrollbar_region = Region(
                scrollbar_region.x + 1,
                scrollbar_region.y,
                scrollbar_region.width,
                scrollbar_region.height + both_on_border,
            )
        elif not getattr(scrollbar, "vertical", True) and border_bottom:
            scrollbar_region = Region(
                scrollbar_region.x,
                scrollbar_region.y + 1,
                scrollbar_region.width + both_on_border,
                scrollbar_region.height,
            )
        yield scrollbar, scrollbar_region


Widget._arrange_scrollbars = arrange_scrollbars  # ty: ignore

_arrange_root = Compositor._arrange_root


def arrange_root(
    self: Compositor, root: Widget, size: Size, visible_only: bool = True
) -> tuple[dict[Widget, MapGeometry], set[Widget]]:
    widget_map, widgets = _arrange_root(self, root, size, visible_only)
    for widget, geometry in widget_map.items():
        if isinstance(widget, ScrollBar) and not geometry.clip.contains_region(
            geometry.region
        ):
            widget_map[widget] = geometry._replace(
                clip=geometry.clip.union(geometry.region)
            )
    return widget_map, widgets


Compositor._arrange_root = arrange_root  # ty: ignore

# with the current implementation it just checks if the character is printable
# problem is that kitty kp sends ctrl+a as a, which is printable, but we don't want
# to consume it, so we need to check if the key is just that key
Input.check_consume_key = lambda self, key, character: (  # ty: ignore
    character
    and len(character) == 1
    and not key.startswith(("ctrl", "shift", "alt", "super"))
    and character.isprintable()
)


# another problem with kitty: Textualize/Textual #6663 - Alt modifier dropped for non-kitty terminals
@lru_cache(maxsize=1024)
def _parse_extended_key(self: XTermParser, sequence: str) -> list[events.Key] | None:
    """Parse a Kitty sequence.

    Args:
        sequence: Input sequence

    Returns:
        Key event, or `None` of none could be parsed.
    """

    if (match := _re_extended_key.fullmatch(sequence)) is None:
        return None

    key_events: list[events.Key] = []

    codes, end = match.groups(default="")
    codepoint_str, modifiers_str, text_str, *_ = codes.split(";") + ["", "", ""]
    codepoint = int(codepoint_str or "1")
    modifiers = int(modifiers_str or "0")

    for text in self._parse_colon_codepoints(text_str):
        if not (key := FUNCTIONAL_KEYS.get(f"{codepoint}{end}", "")):
            key = _character_to_key(text if text else chr(codepoint))

        key_tokens: list[str] = []
        # The modifier is redundant on a modifier key
        if modifiers and key not in MODIFIER_FUNCTIONAL_KEYS and text_str is not None:
            modifier_bits = int(modifiers) - 1
            # Not convinced of the utility in reporting caps_lock and num_lock
            MODIFIERS = ("alt", "ctrl", "super", "hyper", "meta")
            # Ignore caps_lock and num_lock modifiers
            if modifier_bits & 1 and (text is None or text.isspace()):
                key_tokens.append("shift")
            for bit, modifier in enumerate(MODIFIERS, 1):
                # just removing this if statement fixes the problem
                # i'm not sure the context behind this at all
                # if modifier == "alt" and text is not None:
                #     continue
                if modifier_bits & (1 << bit):
                    key_tokens.append(modifier)

        key_tokens.sort()
        if key is not None:
            key_tokens.append(key)
        key_events.append(
            events.Key(
                "+".join(key_tokens),
                text
                or (None if modifiers else SPECIAL_KEY_TO_CHARACTER.get(key, None)),
            )
        )
    return key_events


XTermParser._parse_extended_key = _parse_extended_key  # ty: ignore
