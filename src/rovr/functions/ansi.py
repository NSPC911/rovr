import os
from collections.abc import Iterator
from functools import lru_cache
from itertools import batched

from rich.color import Color
from rich.style import Style
from rich.text import Span, Text


@lru_cache(maxsize=256)  # obviously 256 because of the 256-color palette
def get_ansi_color(number: int) -> Color:
    return Color.from_ansi(number)


def _bat_preview_chunks(lines: list[str], chunk_line_count: int) -> Iterator[str]:
    return ("".join(chunk) for chunk in batched(lines, chunk_line_count))


def ansi_to_rich_text_parallel(
    terminal_text: str,
    *,
    chunk_line_count: int = 5000,
) -> Text:
    """Convert ANSI output to Rich text in process-parallel line chunks.

    Returns:
        Text with ANSI escape sequences represented as Rich spans.
    """
    lines = terminal_text.splitlines(keepends=True)
    chunk_count = (len(lines) + chunk_line_count - 1) // chunk_line_count
    if chunk_count <= 1:
        return ansi_to_rich_text(terminal_text)

    from rovr.functions.multiprocessing_utils import safe_path_process_pool

    max_workers = min(chunk_count, os.cpu_count() or 1)
    if max_workers <= 1:
        return ansi_to_rich_text(terminal_text)

    chunks = _bat_preview_chunks(lines, chunk_line_count)
    combined = Text()
    with safe_path_process_pool(max_workers=max_workers) as executor:
        for text in executor.map(ansi_to_rich_text, chunks):
            combined.append_text(text)
    return combined


def ansi_to_rich_text(terminal_text: str) -> Text:
    """Convert terminal output containing ANSI sequences to Rich text.

    Returns:
        Text with ANSI escape sequences represented as Rich spans.
    """
    if "\r" in terminal_text:
        terminal_text = "\n".join(
            line.rsplit("\r", 1)[-1] for line in terminal_text.splitlines()
        )

    parts: list[str] = []
    spans: list[Span] = []
    style_cache: dict[tuple[object, ...], Style] = {}
    rgb_cache: dict[tuple[int, int, int], Color] = {}
    text_length = 0

    foreground: Color | None = None
    background: Color | None = None
    bold: bool | None = None
    dim: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    blink: bool | None = None
    blink2: bool | None = None
    reverse: bool | None = None
    conceal: bool | None = None
    strike: bool | None = None
    underline2: bool | None = None
    frame: bool | None = None
    encircle: bool | None = None
    overline: bool | None = None
    link: str | None = None

    def append_plain(plain: str) -> None:
        nonlocal text_length
        if not plain:
            return

        start = text_length
        text_length += len(plain)
        parts.append(plain)
        style_key = (
            foreground,
            background,
            bold,
            dim,
            italic,
            underline,
            blink,
            blink2,
            reverse,
            conceal,
            strike,
            underline2,
            frame,
            encircle,
            overline,
            link,
        )
        if not any(value is not None for value in style_key):
            return

        style = style_cache.get(style_key)
        if style is None:
            style = style_cache[style_key] = Style(
                color=foreground,
                bgcolor=background,
                bold=bold,
                dim=dim,
                italic=italic,
                underline=underline,
                blink=blink,
                blink2=blink2,
                reverse=reverse,
                conceal=conceal,
                strike=strike,
                underline2=underline2,
                frame=frame,
                encircle=encircle,
                overline=overline,
                link=link,
            )
        if spans and spans[-1].end == start and spans[-1].style == style:
            previous = spans[-1]
            spans[-1] = Span(previous.start, text_length, style)
        else:
            spans.append(Span(start, text_length, style))

    position = 0
    while position < len(terminal_text):
        escape = terminal_text.find("\x1b", position)
        if escape == -1:
            append_plain(terminal_text[position:])
            break
        append_plain(terminal_text[position:escape])
        if escape + 1 >= len(terminal_text):
            break

        sequence_type = terminal_text[escape + 1]
        if sequence_type == "[":
            sequence_end = escape + 2
            while sequence_end < len(terminal_text) and not (
                "@" <= terminal_text[sequence_end] <= "~"
            ):
                sequence_end += 1
            if sequence_end >= len(terminal_text):
                break

            if terminal_text[sequence_end] == "m":
                parameters = terminal_text[escape + 2 : sequence_end]
                codes = [
                    min(255, int(code) if code else 0)
                    for code in parameters.split(";")
                    if code.isdigit() or code == ""
                ]
                code_index = 0
                while code_index < len(codes):
                    match codes[code_index]:
                        case 0:
                            foreground = background = None
                            bold = dim = italic = underline = None
                            blink = blink2 = reverse = conceal = None
                            strike = underline2 = frame = encircle = overline = None
                            link = None
                        case 1:
                            bold = True
                        case 2:
                            dim = True
                        case 3:
                            italic = True
                        case 4:
                            underline = True
                        case 5:
                            blink = True
                        case 6:
                            blink2 = True
                        case 7:
                            reverse = True
                        case 8:
                            conceal = True
                        case 9:
                            strike = True
                        case 21:
                            underline2 = True
                        case 22:
                            bold = dim = False
                        case 23:
                            italic = False
                        case 24:
                            underline = False
                        case 25:
                            blink = False
                        case 26:
                            blink2 = False
                        case 27:
                            reverse = False
                        case 28:
                            conceal = False
                        case 29:
                            strike = False
                        case code if 30 <= code <= 37:
                            foreground = get_ansi_color(code - 30)
                        case 39:
                            foreground = Color.default()
                        case code if 40 <= code <= 47:
                            background = Color.from_ansi(code - 40)
                        case 49:
                            background = Color.default()
                        case 51:
                            frame = True
                        case 52:
                            encircle = True
                        case 53:
                            overline = True
                        case 54:
                            frame = encircle = False
                        case 55:
                            overline = False
                        case code if 90 <= code <= 97:
                            foreground = get_ansi_color(code - 82)
                        case code if 100 <= code <= 107:
                            background = get_ansi_color(code - 92)
                        case code if code in (38, 48) and code_index + 1 < len(codes):
                            code_index += 1
                            color_type = codes[code_index]
                            color: Color | None = None
                            if color_type == 5 and code_index + 1 < len(codes):
                                code_index += 1
                                color = get_ansi_color(codes[code_index])
                            elif color_type == 2 and code_index + 3 < len(codes):
                                rgb = (
                                    codes[code_index + 1],
                                    codes[code_index + 2],
                                    codes[code_index + 3],
                                )
                                color = rgb_cache.get(rgb)
                                if color is None:
                                    color = rgb_cache[rgb] = Color.from_rgb(*rgb)
                                code_index += 3
                            if color is not None:
                                if code == 38:
                                    foreground = color
                                else:
                                    background = color
                    code_index += 1
            position = sequence_end + 1
            continue

        if sequence_type == "]":
            bell_end = terminal_text.find("\x07", escape + 2)
            string_end = terminal_text.find("\x1b\\", escape + 2)
            ends = [end for end in (bell_end, string_end) if end != -1]
            if not ends:
                break
            sequence_end = min(ends)
            osc = terminal_text[escape + 2 : sequence_end]
            if osc.startswith("8;"):
                _, separator, target = osc[2:].partition(";")
                if separator:
                    link = target or None
            position = sequence_end + (2 if sequence_end == string_end else 1)
            continue

        position = escape + 2

    return Text("".join(parts), spans=spans)


__all__ = ["ansi_to_rich_text", "ansi_to_rich_text_parallel"]
