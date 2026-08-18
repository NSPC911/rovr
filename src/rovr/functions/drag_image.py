from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from importlib import resources
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps
from textual.color import Color, ColorParseError
from textual_drivers.dnd import ImageLabel

HEIGHT = 48
MAX_WIDTH = 480
TEXT_SIZE = 28
ICON_SIZE = 30
ICON_SLOT_WIDTH = 32
PADDING_X = 18
ICON_TEXT_GAP = 12
CORNER_RADIUS = 13
MAX_TEXT_CHARS = 30
SCALE = 2
IMAGE_LABEL_SIZE = 350
IMAGE_PADDING = 12
IMAGE_PREVIEW_SIZE = (
    IMAGE_LABEL_SIZE - (IMAGE_PADDING * 2),
    IMAGE_LABEL_SIZE - HEIGHT - IMAGE_PADDING,
)
ICON_FONT_PATH = (
    resources.files("_rovr.assets")
    if globals().get("__compiled__")
    else resources.files("rovr.assets")
) / "fonts/SymbolsNerdFont-Regular.ttf"


def render_drag_image(
    icon: str,
    text: str,
    icon_color: str,
    theme_variables: dict[str, str],
    image_path: str | None = None,
) -> ImageLabel | None:
    """Render an icon and label into a compact Kitty drag image.

    Returns:
        The rendered PNG label, or None when no suitable font can be loaded.
    """
    # Nerd Font icons may come from a different fallback than Kitty's primary
    # text font, so resolve the two independently.
    text_font_path = _resolve_font_path()
    if text_font_path is None:
        return None

    foreground = _theme_color(theme_variables, "foreground", (231, 237, 245))
    background = _theme_color(theme_variables, "surface", (21, 32, 54))

    if image_path is not None:
        try:
            preview = _load_image_preview(
                image_path,
                os.stat(image_path).st_mtime_ns,
            )
            text_font = _load_font(text_font_path, TEXT_SIZE)
        except (OSError, ValueError):
            pass
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            print(
                "Warning: Image is too large to render as a drag image. Skipping preview."
            )
        else:
            measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            text = _fit_text(
                measure,
                _sanitize_text(text),
                text_font,
                (IMAGE_LABEL_SIZE - PADDING_X * 2),
            )
            text_width = round(measure.textlength(text, font=text_font))
            width = min(
                IMAGE_LABEL_SIZE,
                max(preview.width + IMAGE_PADDING * 2, text_width + PADDING_X * 2),
            )
            height = preview.height + HEIGHT + IMAGE_PADDING
            image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle(
                (0, 0, width - 1, height - 1),
                radius=CORNER_RADIUS,
                fill=(*background, 232),
            )
            image.alpha_composite(
                preview, ((width - preview.width) // 2, IMAGE_PADDING)
            )
            draw.text(
                (width / 2, IMAGE_PADDING + preview.height + HEIGHT / 2),
                text,
                font=text_font,
                fill=(*foreground, 255),
                anchor="mm",
            )
            output = BytesIO()
            image.save(output, format="PNG", compress_level=1)
            return ImageLabel(output.getvalue(), width, height)

    try:
        text_font = _load_font(text_font_path, TEXT_SIZE * SCALE)
        icon_font = _load_font(
            str(ICON_FONT_PATH) if icon else text_font_path,
            ICON_SIZE * SCALE,
        )
    except OSError:
        return None

    resolved_icon_color = _parse_color(icon_color, foreground)

    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    max_text_width = (
        MAX_WIDTH - PADDING_X * 2 - ICON_SLOT_WIDTH - ICON_TEXT_GAP
    ) * SCALE
    text = _fit_text(measure, _sanitize_text(text), text_font, max_text_width)
    text_width = round(measure.textlength(text, font=text_font) / SCALE)
    width = min(
        MAX_WIDTH,
        PADDING_X * 2 + ICON_SLOT_WIDTH + ICON_TEXT_GAP + text_width,
    )

    # Draw at 2x and downsample for smoother corners and glyph edges.
    image = Image.new("RGBA", (width * SCALE, HEIGHT * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width * SCALE - 1, HEIGHT * SCALE - 1),
        radius=CORNER_RADIUS * SCALE,
        fill=(*background, 232),
    )

    icon_center = (PADDING_X + ICON_SLOT_WIDTH / 2) * SCALE
    center_y = HEIGHT * SCALE / 2
    draw.text(
        (icon_center, center_y),
        icon,
        font=icon_font,
        fill=(*resolved_icon_color, 255),
        anchor="mm",
    )
    draw.text(
        ((PADDING_X + ICON_SLOT_WIDTH + ICON_TEXT_GAP) * SCALE, center_y),
        text,
        font=text_font,
        fill=(*foreground, 255),
        anchor="lm",
    )

    image = image.resize((width, HEIGHT), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="PNG")
    return ImageLabel(output.getvalue(), width, HEIGHT)


@lru_cache(maxsize=16)
def _load_image_preview(image_path: str, _modified_ns: int) -> Image.Image:
    with Image.open(image_path) as source:
        max_dimension = max(IMAGE_PREVIEW_SIZE)
        source.draft(None, (max_dimension, max_dimension))
        source.thumbnail(
            (max_dimension, max_dimension),
            Image.Resampling.NEAREST,
            reducing_gap=1.0,
        )
        preview = ImageOps.exif_transpose(source)
        preview.thumbnail(
            IMAGE_PREVIEW_SIZE,
            Image.Resampling.NEAREST,
            reducing_gap=1.0,
        )
        mask = Image.new("L", preview.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (0, 0, preview.width - 1, preview.height - 1),
            radius=CORNER_RADIUS,
            fill=255,
        )
        preview.putalpha(mask)
        return preview.convert("RGBA")


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    text = text[:MAX_TEXT_CHARS]
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return text + ellipsis


def _sanitize_text(text: str) -> str:
    return "".join(
        character if character.isprintable() else " " for character in text
    ).strip()


def _theme_color(
    theme_variables: dict[str, str], key: str, fallback: tuple[int, int, int]
) -> tuple[int, int, int]:
    value = theme_variables.get(key, "")
    if value == "ansi_default":
        # ANSI default has no concrete RGB value outside the terminal.
        ansi_key = "ansi-foreground" if key == "foreground" else "ansi-background"
        value = theme_variables.get(ansi_key, "")
    return _parse_color(value, fallback)


def _parse_color(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert a color string into an RGB Tuple

    Args:
        value (str): The color string to parse.
        fallback (tuple[int, int, int]): The fallback RGB value if parsing fails.

    Returns:
        tuple[int, int, int]: The parsed RGB value, or the fallback if parsing fails
    """
    try:
        color = Color.parse(value)
    except ColorParseError:
        return fallback
    if color.ansi == -1:
        return fallback
    return color.r, color.g, color.b


@lru_cache(maxsize=1)
def _resolve_font_path() -> str | None:
    return _fontconfig_match("monospace")


@lru_cache(maxsize=4)
def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size)


def _fontconfig_match(pattern: str) -> str | None:
    """Check a pattern against the system fontconfig database and return the path to the first matching font file, if any.

    Args:
        pattern (str): The fontconfig pattern to match.

    Returns:
        str | None: The path to the matching font file, or None if no match was
    """
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}\n", pattern],
            capture_output=True,
            check=False,
            text=True,
            timeout=0.5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    font_path = result.stdout.splitlines()[0] if result.stdout else ""
    return font_path if os.path.isfile(font_path) else None


__all__ = ["render_drag_image"]
