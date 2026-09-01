from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Sequence
from typing import cast, overload

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


class LazyTextLines(Sequence[Text]):
    def __init__(
        self,
        line_count: int,
        page_size: int,
        request_page: Callable[[int], None],
        *,
        max_pages: int = 8,
    ) -> None:
        self._line_count = max(line_count, 1)
        self.page_size = page_size
        self._request_page = request_page
        self._max_pages = max_pages
        self._pages: OrderedDict[int, list[Text]] = OrderedDict()
        self._requested: set[int] = set()

    def __len__(self) -> int:
        return self._line_count

    @overload
    def __getitem__(self, index: int) -> Text: ...

    @overload
    def __getitem__(self, index: slice) -> list[Text]: ...

    def __getitem__(self, index: int | slice) -> Text | list[Text]:
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            return [self[line] for line in range(start, stop, step)]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)

        page = index // self.page_size
        lines = self._pages.get(page)
        if lines is None:
            if page not in self._requested:
                self._requested.add(page)
                self._request_page(page)
            return Text()
        self._pages.move_to_end(page)
        return lines[index % self.page_size]

    def set_page(self, page: int, lines: list[Text]) -> None:
        page_start = page * self.page_size
        expected = min(self.page_size, len(self) - page_start)
        self._pages[page] = lines[:expected] + [Text()] * max(0, expected - len(lines))
        self._pages.move_to_end(page)
        self._requested.discard(page)
        while len(self._pages) > self._max_pages:
            self._pages.popitem(last=False)

    def set_line_count(self, line_count: int) -> None:
        self._line_count = max(line_count, 1)


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
        lines: Sequence[str] | Sequence[Text],
        *,
        language: str | None = None,
        line_numbers: bool = False,
        classes: str | None = None,
    ) -> None:
        super().__init__(classes=classes, can_focus=True)
        self._lines: Sequence[str] | Sequence[Text] = []
        self._language = language
        self._line_numbers = line_numbers
        self._gutter_width = 0
        self._rendered_window: tuple[int, int, int, int, list[Strip]] | None = None
        self.update_preview(lines, language=language, line_numbers=line_numbers)

    def update_preview(
        self,
        lines: Sequence[str] | Sequence[Text],
        *,
        language: str | None = None,
        line_numbers: bool = False,
    ) -> None:
        lines = lines or [""]
        if language is not None:
            highlighted = Syntax(
                "",
                lexer=language,
                theme=config["theme"]["preview"],
                background_color=(
                    "default" if config["theme"]["transparent"] else None
                ),
            ).highlight("\n".join(cast(Sequence[str], lines)))
            self._lines = list(highlighted.split("\n", allow_blank=True))[: len(lines)]
        else:
            self._lines = lines
        self._language = None
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
        text_lines = [
            line.copy() if isinstance(line, Text) else Text(line) for line in selected
        ]
        if self._line_numbers:
            for offset, line in enumerate(text_lines):
                number = start + offset + 1
                text_lines[offset] = Text.assemble(
                    (f"{number:>{self._gutter_width - 1}} ", "dim"), line
                )
        renderable = Text("\n", no_wrap=True, overflow="crop").join(text_lines)

        options = self.app.console.options.update(width=max(x + width, 1))
        background = self.visual_style.rich_style
        return [
            Strip(segments).crop(x, x + width).adjust_cell_length(width, background)
            for segments in self.app.console.render_lines(
                renderable, options, pad=False, new_lines=False
            )
        ]

    def set_lazy_page(
        self, source: LazyTextLines, page: int, lines: list[Text]
    ) -> None:
        if self._lines is not source:
            return
        source.set_page(page, lines)
        self.virtual_size = Size(self.virtual_size.width, len(source))
        self._rendered_window = None
        self.refresh(layout=True)

    def set_lazy_line_count(self, source: LazyTextLines, line_count: int) -> None:
        if self._lines is not source:
            return
        source.set_line_count(line_count)
        self.virtual_size = Size(self.virtual_size.width, len(source))
        self._rendered_window = None
        self.refresh(layout=True)

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


__all__ = ["LazyTextLines", "WindowedTextPreview", "_decode_text_preview"]
