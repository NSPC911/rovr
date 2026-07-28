"""Textual widget support for the iTerm2 Inline Image Protocol."""

import os
import sys
from typing import IO, Iterable, NamedTuple

from PIL import Image as PILImage
from rich.console import Console, ConsoleOptions, RenderResult
from rich.control import Control
from rich.measure import Measurement
from rich.segment import ControlType, Segment
from rich.style import Style
from textual.app import ComposeResult
from textual.dom import NoScreen
from textual.geometry import Region, Size
from textual.strip import Strip
from textual.widget import Widget
from textual_image._geometry import ImageSize
from textual_image._pixeldata import PixelData
from textual_image._terminal import CellSize, get_cell_size
from textual_image._utils import StrOrBytesPath
from textual_image.widget._base import Image as BaseImage
from typing_extensions import override

_NULL_STYLE = Style()


def is_supported() -> bool:
    """Return whether the active terminal supports iTerm2 inline images.

    Returns:
        Whether the terminal advertises iTerm2 Inline Image Protocol support.
    """
    return bool(
        sys.__stdout__
        and sys.__stdout__.isatty()
        and os.environ.get("TERM_PROGRAM") in ("iTerm2", "WezTerm")
    )


def _build_sequence(image_data_b64: str, pixel_width: int, pixel_height: int) -> str:
    return (
        "\x1b]1337;File="
        f"inline=1;width={pixel_width}px;height={pixel_height}px;preserveAspectRatio=0"
        f":{image_data_b64}\x07"
    )


class _CachedImageData(NamedTuple):
    image: StrOrBytesPath | IO[bytes] | PILImage.Image
    content_crop: Region
    content_size: Size
    terminal_sizes: CellSize
    data: str

    def is_hit(
        self,
        image: StrOrBytesPath | IO[bytes] | PILImage.Image,
        content_crop: Region,
        content_size: Size,
        terminal_sizes: CellSize,
    ) -> bool:
        return (
            image == self.image
            and content_crop == self.content_crop
            and content_size == self.content_size
            and terminal_sizes == self.terminal_sizes
        )


class _NoopRenderable:
    def __init__(
        self,
        image: StrOrBytesPath | IO[bytes] | PILImage.Image,
        width: int | str | None = None,
        height: int | str | None = None,
    ) -> None:
        pass

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield Segment("")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(0, 0)

    def cleanup(self) -> None:
        pass


class ITerm2Image(BaseImage, Renderable=_NoopRenderable):
    """Render an image through the iTerm2 Inline Image Protocol."""

    @override
    @BaseImage.image.setter
    def image(self, value: StrOrBytesPath | IO[bytes] | PILImage.Image | None) -> None:
        super(__class__, type(self)).image.fset(self, value)
        self.refresh(recompose=True)

    def compose(self) -> ComposeResult:
        yield _ImageImpl(self.image)


class _ImageImpl(Widget, can_focus=False, inherit_css=False):
    DEFAULT_CSS = """
    _ImageImpl {
        width: 100%;
        height: 100%;
    }
    """

    @override
    def __init__(
        self,
        image: StrOrBytesPath | IO[bytes] | PILImage.Image | None = None,
    ) -> None:
        super().__init__()
        self.image = image
        self._cached_data: _CachedImageData | None = None

    @override
    def render_lines(self, crop: Region) -> list[Strip]:
        try:
            if not self.image or not self.screen.is_active:
                return []
        except NoScreen:
            return []

        terminal_sizes = get_cell_size()
        if self._cached_data and self._cached_data.is_hit(
            self.image, crop, self.content_size, terminal_sizes
        ):
            data = self._cached_data.data
        else:
            image_data = PixelData(self.image)
            image_data = self._scale_image(image_data, terminal_sizes)
            image_data = self._crop_image(image_data, crop, terminal_sizes)
            data = _build_sequence(
                image_data.to_base64(),
                crop.width * terminal_sizes.width,
                crop.height * terminal_sizes.height,
            )
            self._cached_data = _CachedImageData(
                self.image, crop, self.content_size, terminal_sizes, data
            )

        clear_segment = Segment(" " * crop.width, style=self._get_clear_style())
        image_segments = self._get_image_segments(data)
        lines = [
            Strip([clear_segment], cell_length=crop.width)
            for _ in range(crop.height - 1)
        ]
        lines.append(Strip([clear_segment, *image_segments], cell_length=crop.width))
        return lines

    def _scale_image(
        self, image_data: PixelData, terminal_sizes: CellSize
    ) -> PixelData:
        assert isinstance(self.parent, ITerm2Image)
        styled_width, styled_height = self.parent._get_styled_size()
        image_size = ImageSize(
            image_data.width,
            image_data.height,
            width=styled_width,
            height=styled_height,
        )
        pixel_width, pixel_height = image_size.get_pixel_size(
            self.content_size.width, self.content_size.height, terminal_sizes
        )
        return image_data.scaled(pixel_width, pixel_height)

    def _crop_image(
        self, image: PixelData, crop: Region, terminal_sizes: CellSize
    ) -> PixelData:
        return image.cropped(
            crop.x * terminal_sizes.width,
            crop.y * terminal_sizes.height,
            crop.right * terminal_sizes.width,
            crop.bottom * terminal_sizes.height,
        )

    def _get_image_segments(self, data: str) -> Iterable[Segment]:
        visible_region = self.screen.find_widget(self).visible_region
        return [
            Segment(
                Control.move_to(visible_region.x, visible_region.y).segment.text,
                style=_NULL_STYLE,
            ),
            Segment(
                data, style=_NULL_STYLE, control=((ControlType.CURSOR_FORWARD, 0),)
            ),
            Segment(
                Control.move_to(
                    visible_region.right, visible_region.bottom - 2
                ).segment.text,
                style=_NULL_STYLE,
            ),
        ]

    def _get_clear_style(self) -> Style:
        _, color = self.background_colors
        return Style(bgcolor=color.rich_color)
