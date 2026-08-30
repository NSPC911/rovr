from __future__ import annotations

from typing import cast

from rich.cells import cell_len
from rich.syntax import Syntax
from rich.text import Text
from textual.geometry import Size
from textual.scroll_view import ScrollView
from textual.strip import Strip

from rovr.variables.constants import config

TEXT_ENCODINGS = (
    "utf8",
    "utf16",
    "utf32",
    "latin1",
    "iso8859-1",
    "mbcs",
    "ascii",
    "us-ascii",
)


def _decode_text_preview(data: bytes, truncated: bool) -> tuple[str, int] | None:
    for encoding in TEXT_ENCODINGS:
        try:
            return data.decode(encoding), 0
        except UnicodeDecodeError as exc:
            if truncated and exc.end == len(data):
                try:
                    return data[: exc.start].decode(encoding), len(data) - exc.start
                except UnicodeDecodeError:
                    pass
    return None


class WindowedTextPreview(ScrollView):
    """Render only the visible portion of a text preview."""

    DEFAULT_CSS = """
    WindowedTextPreview {
        width: 1fr;
        height: 1fr;
        padding: 0;
        scrollbar-size: 1 1;
    }
    """

    def __init__(
        self,
        lines: list[str] | list[Text],
        *,
        language: str | None = None,
        line_numbers: bool = False,
        classes: str | None = None,
    ) -> None:
        super().__init__(classes=classes, can_focus=True)
        self._lines: list[str] | list[Text] = []
        self._language = language
        self._line_numbers = line_numbers
        self._gutter_width = 0
        self._rendered_window: tuple[int, int, int, int, list[Strip]] | None = None
        self.update_preview(lines, language=language, line_numbers=line_numbers)

    def update_preview(
        self,
        lines: list[str] | list[Text],
        *,
        language: str | None = None,
        line_numbers: bool = False,
    ) -> None:
        self._lines = lines or [""]
        self._language = language
        self._line_numbers = line_numbers
        self._gutter_width = len(str(len(self._lines))) + 3 if line_numbers else 0
        width = max(
            cell_len((line.plain if isinstance(line, Text) else line).expandtabs(4))
            for line in self._lines[:256]
        )
        self.virtual_size = Size(width + self._gutter_width, len(self._lines))
        self._rendered_window = None
        self.scroll_home(animate=False)
        self.refresh(layout=True)

    def _render_window(self, start: int, width: int, x: int) -> list[Strip]:
        end = min(
            start + max(self.scrollable_content_region.height, 1), len(self._lines)
        )
        selected = self._lines[start:end]
        window_width = max(
            cell_len((line.plain if isinstance(line, Text) else line).expandtabs(4))
            for line in selected
        )
        if window_width + self._gutter_width > self.virtual_size.width:
            self.virtual_size = Size(
                window_width + self._gutter_width, self.virtual_size.height
            )
            self._scroll_update(self.virtual_size)
        if self._language is not None:
            renderable: Text | Syntax = Syntax(
                "\n".join(cast(list[str], selected)),
                lexer=self._language,
                line_numbers=self._line_numbers,
                start_line=start + 1,
                word_wrap=False,
                tab_size=4,
                theme=config["theme"]["preview"],
                background_color=(
                    "default" if config["theme"]["transparent"] else None
                ),
                padding=0,
            )
        else:
            renderable = Text("\n", no_wrap=True, overflow="crop").join(
                cast(list[Text], selected)
            )

        options = self.app.console.options.update(width=max(x + width, 1))
        background = self.visual_style.rich_style
        return [
            Strip(segments).crop(x, x + width).adjust_cell_length(width, background)
            for segments in self.app.console.render_lines(
                renderable, options, pad=False, new_lines=False
            )
        ]

    def render_line(self, y: int) -> Strip:
        width = self.scrollable_content_region.width
        height = self.scrollable_content_region.height
        start = int(self.scroll_offset.y)
        x = int(self.scroll_offset.x)
        cache = self._rendered_window
        if cache is None or cache[:4] != (start, width, height, x):
            lines = self._render_window(start, width, x)
            cache = self._rendered_window = (start, width, height, x, lines)
        try:
            return cache[4][y]
        except IndexError:
            return Strip.blank(width, self.visual_style.rich_style)


__all__ = ["WindowedTextPreview", "_decode_text_preview"]
