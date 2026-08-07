from __future__ import annotations

import glob
import os
import shlex
import subprocess
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from platformdirs import user_config_path
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
    """Resolve a font path for the given character, or for Kitty's configured font family.

    Args:
        character (str): The character to find a font for. If empty, will use Kitty's configured font family.

    Returns:
        str | None: The path to the font file, or None if no suitable font could
    """
    if character:
        matched = _fontconfig_match(f":charset={ord(character):x}")
        if matched is not None:
            return matched

    family = _kitty_font_family()
    if family:
        if (matched := _fontconfig_match(family)) is not None:
            return matched
        if (matched := _system_font_for_family(family)) is not None:
            return matched

    if character and (matched := _system_nerd_font()) is not None:
        return matched
    try:
        if family:
            font = ImageFont.truetype(family, 12)
    except OSError:
        return
    else:
        return str(font.path)


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


@lru_cache(maxsize=16)
def _system_font_for_family(family: str) -> str | None:
    family = family.casefold()
    for font_path in _system_font_files():
        try:
            name = ImageFont.truetype(font_path, 12).getname()[0]
        except OSError:
            continue
        if family in name.casefold() or name.casefold() in family:
            return font_path
    return None


@lru_cache(maxsize=1)
def _system_nerd_font() -> str | None:
    """Find literally any reasonable Nerd Font installed on system

    Returns:
        str | None: The path to the first matching Nerd Font file, or None if no"""
    for font_path in _system_font_files():
        try:
            name = ImageFont.truetype(font_path, 12).getname()[0].casefold()
        except OSError:
            continue
        if "nerd font" in name or "symbols nerd" in name:
            return font_path
    return None


@lru_cache(maxsize=1)
def _system_font_files() -> tuple[str, ...]:
    # Fontconfig is not normally available on macOS or Windows, so scan their
    # standard font directories as a portable fallback.
    # TODO: make sure to make it OS Independent when WezTerm adds support
    # for DND on Windows (cant wait)
    roots = (
        Path.home() / ".local" / "share" / "fonts",
        Path.home() / "Library" / "Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
    )
    return tuple(
        str(font_path)
        for root in roots
        if root.is_dir()
        for font_path in root.rglob("*")
        if font_path.suffix.casefold() in {".otf", ".ttc", ".ttf"}
    )


@lru_cache(maxsize=1)
def _kitty_font_family() -> str | None:
    """Return the font family configured in Kitty, if any.

    Returns:
        str | None: The font family if found, otherwise None
    """
    candidates: list[Path] = []
    if config_directory := os.environ.get("KITTY_CONFIG_DIRECTORY"):
        candidates.append(Path(config_directory) / "kitty.conf")
    if xdg_config_home := os.environ.get("XDG_CONFIG_HOME"):
        candidates.append(Path(xdg_config_home) / "kitty" / "kitty.conf")
    candidates.append(user_config_path("kitty") / "kitty.conf")

    for candidate in dict.fromkeys(candidates):
        if family := _read_font_family(candidate, set(), 0):
            return family
    return None


def _read_font_family(config_path: Path, seen: set[Path], depth: int) -> str | None:
    """Manual kitty config parsing

    We are looking specifically for phrases like `font_family FOO`
    ╰─> If `include` is found, we  will recursively do the same to it

    Args:
        config_path (Path): Path to the kitty config file
        seen (set[Path]): Set of already seen config paths to avoid infinite recursion
        depth (int): Current recursion depth

    Returns:
        str | None: The font family if found, otherwise None
    """
    if depth > 8:
        return None
    try:
        config_path = config_path.expanduser().resolve()
        if config_path in seen:
            return None
        seen.add(config_path)
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    family: str | None = None
    for line in lines:
        try:
            parts = shlex.split(line, comments=True)
        except ValueError:
            continue
        if len(parts) < 2:
            continue
        key, values = parts[0], parts[1:]
        if key == "include":
            # Relative includes are resolved from the file containing them.
            value = " ".join(values)
            pattern = Path(value).expanduser()
            if not pattern.is_absolute():
                pattern = config_path.parent / pattern
            for included in sorted(glob.glob(str(pattern))):
                if included_family := _read_font_family(
                    Path(included), seen, depth + 1
                ):
                    family = included_family
        elif key == "font_family" and values != ["auto"]:
            family = _family_name(values)
    return family


def _family_name(values: list[str]) -> str | None:
    first = values[0]
    if "=" not in first:
        return " ".join(values)
    key, _, value = first.partition("=")
    return value if key in {"family", "postscript_name", "system"} else None


__all__ = ["render_drag_image"]
