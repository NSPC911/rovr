from pathlib import Path

from PIL import Image

from rovr.functions.preview_utils import (
    MAX_IMAGE_SIZE,
    resample_batch_sync,
    resample_file_sync,
    resample_sync,
)


def test_resample_sync_preserves_aspect_ratio() -> None:
    image = Image.new("RGB", (MAX_IMAGE_SIZE[0] * 2, MAX_IMAGE_SIZE[1]))

    assert resample_sync(image).size == (MAX_IMAGE_SIZE[0], MAX_IMAGE_SIZE[1] // 2)


def test_resample_file_sync_preserves_aspect_ratio(tmp_path: Path) -> None:
    image_path = tmp_path / "wide.png"
    Image.new("RGB", (MAX_IMAGE_SIZE[0] * 2, MAX_IMAGE_SIZE[1])).save(image_path)

    assert resample_file_sync(str(image_path)).size == (
        MAX_IMAGE_SIZE[0],
        MAX_IMAGE_SIZE[1] // 2,
    )


def test_resample_batch_sync_preserves_aspect_ratio() -> None:
    images = [Image.new("RGB", (MAX_IMAGE_SIZE[0] * 2, MAX_IMAGE_SIZE[1]))]

    assert resample_batch_sync(images)[0].size == (
        MAX_IMAGE_SIZE[0],
        MAX_IMAGE_SIZE[1] // 2,
    )
