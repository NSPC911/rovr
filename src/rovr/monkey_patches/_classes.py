from typing import IO, Iterable, cast

from PIL import Image as PILImage
from rich.ansi import AnsiDecoder
from rich.color import Color
from rich.color_triplet import ColorTriplet
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual_image import _pixeldata
from textual_image._geometry import ImageSize
from textual_image._terminal import get_cell_size
from textual_image._utils import StrOrBytesPath, grouped
from textual_image.renderable import halfcell

from rovr.variables.constants import RESAMPLING_METHOD


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
                yield Segment("▄", style=Style(color=_map_pixel(lower)))
            elif lower[3] == 0:
                yield Segment("▀", style=Style(color=_map_pixel(upper)))
            else:
                yield Segment(
                    "▀", style=Style(color=_map_pixel(upper), bgcolor=_map_pixel(lower))
                )
        yield Segment("\n")


halfcell.Image.__init__ = halfcell_init  # ty: ignore[invalid-assignment]
halfcell.Image.__rich_console__ = halfcell_rich_console  # ty: ignore[invalid-assignment]


# https://github.com/Textualize/rich/issues/4090
def decode(self: AnsiDecoder, terminal_text: str) -> Iterable[Text]:
    for line in terminal_text.splitlines():
        yield self.decode_line(line)


AnsiDecoder.decode = decode  # ty: ignore[invalid-assignment]
