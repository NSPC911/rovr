import re
from typing import Iterable

from rich.ansi import AnsiDecoder
from rich.text import Text
from textual_image import _pixeldata

from rovr.variables.constants import RESAMPLING_METHOD


def scaled(self: _pixeldata.PixelData, width: int, height: int) -> _pixeldata.PixelData:
    scaled_image = self._image.resize((width, height), resample=RESAMPLING_METHOD)
    return _pixeldata.PixelData(scaled_image)


_pixeldata.PixelData.scaled = scaled  # ty: ignore[invalid-assignment]


# https://github.com/Textualize/rich/issues/4090
def decode(self: AnsiDecoder, terminal_text: str) -> Iterable[Text]:
    for line in re.split(r"(?<=\n)", terminal_text):
        yield self.decode_line(line.rstrip("\n").rstrip("\r"))


AnsiDecoder.decode = decode  # ty: ignore[invalid-assignment]
