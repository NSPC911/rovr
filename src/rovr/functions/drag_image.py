from __future__ import annotations

import subprocess
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
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


def render_drag_image(
    icon: str,
    text: str,
    icon_color: str,
    theme_variables: dict[str, str],
) -> ImageLabel | None:
    """Render an icon and label into a compact Kitty drag image.

    Returns:
        The rendered PNG label, or None when no suitable font can be loaded.
    """
    # Nerd Font icons may come from a different fallback than Kitty's primary
    # text font, so resolve the two independently.
    text_font_path = _resolve_font_path()
    icon_font_path = _resolve_font_path(icon[0]) if icon else text_font_path
    if text_font_path is None or icon_font_path is None:
        return None

    try:
        text_font = ImageFont.truetype(text_font_path, TEXT_SIZE * SCALE)
        icon_font = ImageFont.truetype(icon_font_path, ICON_SIZE * SCALE)
    except OSError:
        return None

    foreground = _theme_color(theme_variables, "foreground", (231, 237, 245))
    background = _theme_color(theme_variables, "surface", (21, 32, 54))
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


@lru_cache(maxsize=128)
def _resolve_font_path(character: str = "") -> str | None:
    pattern = f":charset={ord(character):x}" if character else "monospace"
    return _fontconfig_match(pattern)


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
    return font_path if Path(font_path).is_file() else None


__all__ = ["render_drag_image"]
