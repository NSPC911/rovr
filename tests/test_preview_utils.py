from pathlib import Path

import pytest
from PIL import Image

from rovr.functions import preview_utils
from rovr.functions.preview_utils import (
    MAX_IMAGE_SIZE,
    match_mime_to_preview_type,
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


def test_mime_rule_extension_refinement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preview_utils,
        "config",
        {
            "settings": {
                "preview_rules": {
                    "application/(x-)?gzip": {
                        "default": "archive",
                        "extensions": {"svgz": "resvg"},
                    },
                    "image/.*": "image",
                    "image/svg\\+xml": "resvg",
                }
            }
        },
    )
    match_mime_to_preview_type.cache_clear()

    assert match_mime_to_preview_type("application/gzip", ".svgz") == "resvg"
    assert match_mime_to_preview_type("application/x-gzip", ".SVGZ") == "resvg"
    assert match_mime_to_preview_type("application/gzip", ".gz") == "archive"
    assert match_mime_to_preview_type("image/png", ".svgz") == "image"
    assert match_mime_to_preview_type("image/svg+xml", ".svgz") == "resvg"
    match_mime_to_preview_type.cache_clear()
