from textual_image import _pixeldata

from rovr.variables.constants import RESAMPLING_METHOD


def scaled(self: _pixeldata.PixelData, width: int, height: int) -> _pixeldata.PixelData:
    scaled_image = self._image.resize((width, height), resample=RESAMPLING_METHOD)
    return _pixeldata.PixelData(scaled_image)


_pixeldata.PixelData.scaled = scaled  # ty: ignore[invalid-assignment]
