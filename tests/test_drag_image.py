from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageFont
from textual_drivers.dnd import ImageLabel

from rovr.functions import drag_image


@pytest.fixture
def font_path(tmp_path: Path) -> str:
    packaged_font = ImageFont.load_default().path
    assert isinstance(packaged_font, BytesIO)
    font_path = tmp_path / "pillow-default.ttf"
    font_path.write_bytes(packaged_font.getvalue())
    return str(font_path)


def test_render_drag_image_creates_bounded_png(
    monkeypatch: pytest.MonkeyPatch, font_path: str
) -> None:
    monkeypatch.setattr(
        drag_image, "_resolve_font_path", lambda character="": font_path
    )

    label = drag_image.render_drag_image(
        "F",
        "a very long filename that must remain inside the drag card.txt",
        "#daA520",
        {"foreground": "#f0f0f0", "surface": "#152036"},
    )

    assert isinstance(label, ImageLabel)
    assert label.height == drag_image.HEIGHT
    assert label.width <= drag_image.MAX_WIDTH
    with Image.open(BytesIO(label.data)) as image:
        assert image.format == "PNG"
        assert image.size == (label.width, label.height)
        corner = image.convert("RGBA").getpixel((0, 0))
        assert isinstance(corner, tuple)
        assert corner[3] < 232


def test_render_drag_image_returns_none_without_fonts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(drag_image, "_resolve_font_path", lambda character="": None)

    assert drag_image.render_drag_image("F", "file.txt", "white", {}) is None


def test_render_drag_image_sanitizes_multiline_filenames(
    monkeypatch: pytest.MonkeyPatch, font_path: str
) -> None:
    monkeypatch.setattr(
        drag_image, "_resolve_font_path", lambda character="": font_path
    )

    label = drag_image.render_drag_image("F", "line one\nline two", "white", {})

    assert isinstance(label, ImageLabel)


def test_ansi_default_uses_concrete_theme_fallback() -> None:
    variables = {
        "foreground": "ansi_default",
        "ansi-foreground": "ansi_bright_white",
        "surface": "ansi_default",
        "ansi-background": "ansi_black",
    }

    assert drag_image._theme_color(variables, "foreground", (1, 2, 3)) == (
        255,
        255,
        255,
    )
    assert drag_image._theme_color(variables, "surface", (1, 2, 3)) == (0, 0, 0)


def test_font_family_reads_includes_and_last_assignment(tmp_path: Path) -> None:
    included = tmp_path / "fonts.conf"
    included.write_text('font_family "First Font"\n', encoding="utf-8")
    config = tmp_path / "kitty.conf"
    config.write_text(
        'include fonts.conf\nfont_family "CaskaydiaMono Nerd Font Mono"\n',
        encoding="utf-8",
    )

    assert drag_image._font_family_from_config(config) == "CaskaydiaMono Nerd Font Mono"


def test_font_family_parses_kitty_extended_syntax(tmp_path: Path) -> None:
    config = tmp_path / "kitty.conf"
    config.write_text(
        'font_family family="Source Code VF" variable_name=SourceCodeUpright wght=380\n',
        encoding="utf-8",
    )

    assert drag_image._font_family_from_config(config) == "Source Code VF"
