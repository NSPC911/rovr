from typing import cast

from PIL import Image
from rich.console import Console
from rich.segment import Segment
from textual_image.renderable.halfcell import Image as HalfcellImage

import rovr.monkey_patches._classes  # noqa: F401


def _render_pixels(pixels: list[tuple[int, int, int, int]]) -> list[Segment]:
    image = Image.new("RGBA", (1, 2))
    image.putdata(pixels)
    console = Console()
    renderable = HalfcellImage(image, width=1, height=1)
    return [
        cast(Segment, segment)
        for segment in renderable.__rich_console__(
            console, console.options.update(width=1, height=1)
        )
    ]


def test_render_fully_transparent_pixels_as_spaces() -> None:
    segments = _render_pixels([(0, 0, 0, 0), (0, 0, 0, 0)])

    assert segments[0].text == " "
    assert segments[0].style is None


def test_render_single_transparent_halfcell_without_background() -> None:
    segments = _render_pixels([(0, 0, 0, 0), (255, 0, 0, 255)])

    assert segments[0].text == "▄"
    assert segments[0].style is not None
    assert segments[0].style.bgcolor is None


def test_render_single_transparent_halfcell_with_background() -> None:
    segments = _render_pixels([(255, 0, 0, 255), (0, 0, 0, 0)])

    assert segments[0].text == "▀"
    assert segments[0].style is not None
    assert segments[0].style.bgcolor is None
