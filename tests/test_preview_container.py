import asyncio
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from rich.console import Console
from rich.text import Text
from textual.app import App, ComposeResult

from rovr.components.text_preview import (
    LazyTextLines,
    WindowedTextPreview,
    _decode_text_preview,
)
from rovr.core.preview_container import ExitNow, PreviewContainer, preview_token
from rovr.variables.constants import config


class PreviewTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield PreviewContainer()


class WindowedPreviewTestApp(App[None]):
    CSS = "WindowedTextPreview { width: 30; height: 5; }"

    def compose(self) -> ComposeResult:
        yield WindowedTextPreview(
            [f"line {line}" for line in range(10_000)], language="python"
        )


async def test_call_from_thread_rejects_stale_preview() -> None:
    app = PreviewTestApp()

    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        current_token = preview._active_preview_token

        def call_with(token: object) -> int:
            context_token = preview_token.set(token)
            try:
                return preview.call_from_thread(lambda: 42)
            finally:
                preview_token.reset(context_token)

        assert await asyncio.to_thread(call_with, current_token) == 42

        preview._active_preview_token = object()
        with pytest.raises(ExitNow):
            await asyncio.to_thread(call_with, current_token)


async def test_windowed_preview_only_renders_visible_lines() -> None:
    app = WindowedPreviewTestApp()

    async with app.run_test(size=(40, 10)) as pilot:
        preview = app.query_one(WindowedTextPreview)
        await pilot.pause()

        initial_width = preview.virtual_size.width
        preview.render_line(0)
        assert preview.virtual_size.height == 10_000
        assert preview._rendered_window is not None
        assert len(preview._rendered_window[4]) <= preview.size.height

        preview.scroll_end(animate=False)
        await pilot.pause()
        assert preview.scroll_offset.y > 9_000
        assert f"line {int(preview.scroll_offset.y)}" in preview.render_line(0).text
        assert preview.virtual_size.width > initial_width


def test_lazy_text_lines_requests_and_caches_pages() -> None:
    requested: list[int] = []
    lines = LazyTextLines(600, 256, requested.append)
    lines.set_page(0, [Text(f"line {line}") for line in range(256)])

    assert len(lines) == 600
    assert lines[10].plain == "line 10"
    assert lines[300].plain == ""
    assert lines[300].plain == ""
    assert requested == [1]

    lines.set_page(1, [Text(f"line {line}") for line in range(256, 512)])
    assert lines[300].plain == "line 300"


def test_lazy_text_lines_updates_line_count() -> None:
    lines = LazyTextLines(256, 256, lambda page: None)

    lines.set_line_count(600)

    assert len(lines) == 600


async def test_bat_line_count_updates_lazy_source(tmp_path: Path) -> None:
    file = tmp_path / "large.txt"
    file.write_text("line\n" * 600, encoding="utf-8")
    app = PreviewTestApp()

    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        token = preview._active_preview_token
        source = LazyTextLines(256, 256, lambda page: None)
        text_preview = WindowedTextPreview(source)

        with (
            patch("rovr.core.preview_container.load_from_cache", return_value=None),
            patch("rovr.core.preview_container.save_to_cache") as save,
        ):
            await asyncio.to_thread(
                preview._count_bat_lines,
                token,
                text_preview,
                source,
                str(file),
                file.stat(),
                ("test", "bat"),
            )

        assert len(source) == 600
        assert save.call_args.args[4] == "600"


async def test_windowed_preview_preserves_multiline_highlighting() -> None:
    app = App()

    async with app.run_test():
        preview = WindowedTextPreview(
            ["value = '''start", "inside", "end'''", "other = 1"],
            language="python",
        )
        lines = cast(list[Text], preview._lines)
        console = Console()

        string_style = lines[0].get_style_at_offset(console, len(lines[0]) - 1)
        assert lines[1].get_style_at_offset(console, 0) == string_style
        assert lines[3].get_style_at_offset(console, 0) != string_style


async def test_normal_preview_mounts_windowed_content(tmp_path: Path) -> None:
    source = tmp_path / "large.py"
    source.write_text("value = 1\nvalue = 2\n", encoding="utf-8")
    app = PreviewTestApp()

    async with app.run_test(size=(80, 20)) as pilot:
        preview = app.query_one(PreviewContainer)
        preview._current_file_path = str(source)
        token = preview._active_preview_token

        def show_preview() -> None:
            context_token = preview_token.set(token)
            try:
                preview.show_normal_file_preview()
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.core.preview_container.load_from_cache", return_value=None),
            patch("rovr.core.preview_container.save_to_cache"),
        ):
            await asyncio.to_thread(show_preview)
        await pilot.pause()
        text_preview = preview.query_one(WindowedTextPreview)
        assert "value" in text_preview.render_line(0).text


async def test_truncated_preview_is_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "large.txt"
    source.write_bytes(b"first\nsecond\nthird\n")
    monkeypatch.setitem(
        cast(dict[str, Any], config["interface"]["preview_text"]),
        "max_file_size",
        6,
    )
    app = PreviewTestApp()

    async with app.run_test(size=(80, 20)) as pilot:
        preview = app.query_one(PreviewContainer)
        preview._current_file_path = str(source)
        token = preview._active_preview_token

        def show_preview() -> None:
            context_token = preview_token.set(token)
            try:
                preview.show_normal_file_preview()
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.core.preview_container.load_from_cache", return_value=None),
            patch("rovr.core.preview_container.save_to_cache") as save,
        ):
            await asyncio.to_thread(show_preview)
        await pilot.pause()

        cached_content = save.call_args.args[4]
        assert cached_content == "first\n---\n(13 bytes ignored)"

        with (
            patch(
                "rovr.core.preview_container.load_from_cache",
                return_value=cached_content,
            ),
            patch("rovr.core.preview_container.save_to_cache") as save,
        ):
            await asyncio.to_thread(show_preview)
        assert not save.called


def test_truncated_multibyte_character_is_counted_as_ignored() -> None:
    assert _decode_text_preview("é".encode()[:1], truncated=True) == ("", 1)
