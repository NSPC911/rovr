import asyncio
import pickle
import subprocess
from pathlib import Path
from threading import Event
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from rich.console import Console
from rich.text import Text
from textual.app import App, ComposeResult
from textual.content import Content
from textual.widgets import Static

from rovr.app import Application
from rovr.components.text_preview import (
    LazyTextLines,
    WindowedTextPreview,
    _decode_text_preview,
)
from rovr.core.preview_container import PreviewContainer
from rovr.functions.cache import _load_text, _save_text
from rovr.functions.preview_utils import MimeResult
from rovr.functions.utils import ExitNow
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


async def test_video_seek_frames(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image

    source = tmp_path / "clip.mp4"
    source.touch()
    png = BytesIO()
    # The headless renderer can round a 2x2 frame down to zero terminal cells.
    Image.new("RGB", (160, 90)).save(png, format="PNG")
    positions = []

    def popen(command: list[str], **kwargs: Any) -> Mock:
        assert command[command.index("-frames:v") + 1] == "1"
        positions.append(int(command[command.index("-ss") + 1]))
        kwargs["stdout"].write(png.getvalue())
        process = Mock(returncode=0)
        process.poll.return_value = 0
        process.communicate.return_value = (None, None)
        return process

    async with PreviewTestApp().run_test() as pilot:
        preview = pilot.app.query_one(PreviewContainer)
        with (
            patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"11.5")
            ),
            patch("subprocess.Popen", side_effect=popen),
            patch(
                "rovr.functions.preview_utils.get_mime_type",
                return_value=MimeResult("basic", "video/mp4"),
            ),
        ):
            preview.show_preview(str(source), source.stat().st_mtime)
            await pilot.app.workers.wait_for_complete()
            for action, second in [
                ("right", 1),
                ("page_right", 11),
                ("right", 11),
                ("page_left", 1),
                ("left", 0),
            ]:
                getattr(preview, f"action_{action}")()
                await pilot.app.workers.wait_for_complete()
                assert preview.border_subtitle == f"00:{second:02}"
        assert positions == [0, 1, 11, 1, 0]


def test_cached_text_uses_pickle() -> None:
    text = Text.from_markup("[bold red]cached[/]")

    with patch("rovr.functions.cache.save") as save:
        _save_text("file", "bat-page", cast(Any, None), ("v2", "bat"), text)

    data = save.call_args.args[4]
    assert pickle.loads(data) == text
    with patch("rovr.functions.cache.load", return_value=data):
        assert _load_text("file", "bat-page", cast(Any, None), ("v2", "bat")) == text


@pytest.mark.parametrize("exit_code", [0, 21])
async def test_custom_previewer_cleans_browser_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    source = tmp_path / "page.html"
    source.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setitem(
        cast(dict[str, Any], config)["settings"],
        "previewers",
        {
            "test-browser": {
                "command": ["render", "--user-data-dir=%tmpdir", "--screenshot=%file"],
                "file": "%temp.png",
                "type": "image",
            }
        },
    )
    profiles: list[Path] = []

    async def expand(app: App[Any], command: list[str], banned: list[str]) -> list[str]:
        return command

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        profile = Path(command[1].split("=", 1)[1])
        output = Path(command[2].split("=", 1)[1])
        assert profile.is_dir()
        assert output.suffix == ".png"
        profiles.append(profile)
        if exit_code:
            raise subprocess.CalledProcessError(exit_code, command, b"", b"")
        output.write_bytes(b"image-data")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    def mount(mime: bool = True) -> None:
        raise RuntimeError("Was Called")

    app = PreviewTestApp()
    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        preview.mount_special_messages = mount  # ty: ignore[invalid-assignment]
        preview._current_file_path = str(source)
        token = preview._active_preview_token
        preview_token = preview.preview_token

        def show() -> None:
            context_token = preview_token.set(token)
            try:
                preview.show_custom_preview("test-browser")
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.functions.utils.expand_command", expand),
            patch("rovr.core.preview_container.subprocess.run", side_effect=run),
            patch("rovr.functions.cache.load", return_value=None),
            patch("rovr.functions.cache.save"),
            patch.object(preview, "show_image_preview"),
        ):
            if exit_code:
                with pytest.raises(RuntimeError):
                    await asyncio.to_thread(show)
            else:
                await asyncio.to_thread(show)

        assert len(profiles) == 1
        assert not profiles[0].exists()


@pytest.mark.parametrize("preview_type", ["image", "pdf"])
async def test_custom_previewer_renders_from_cached_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, preview_type: str
) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"document")
    cached = tmp_path / "cached"
    monkeypatch.setitem(
        cast(dict[str, Any], config)["settings"],
        "previewers",
        {
            "converted": {
                "command": ["render", "%file"],
                "file": "%temp.pdf" if preview_type == "pdf" else "%temp.png",
                "type": preview_type,
            }
        },
    )

    async def expand(app: App[Any], command: list[str], banned: list[str]) -> list[str]:
        return command

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        Path(command[1]).write_bytes(b"converted")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    def save(*args: Any) -> None:
        cached.write_bytes(args[4])

    def render(*args: Any, **kwargs: Any) -> None:
        assert preview._current_file_path == str(cached)
        assert cached.read_bytes() == b"converted"

    app = PreviewTestApp()
    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        token = preview._active_preview_token
        preview._file_type = "converted"
        preview_token = preview.preview_token

        def show() -> None:
            preview._current_file_path = str(source)
            context_token = preview_token.set(token)
            try:
                preview.show_custom_preview("converted")
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.functions.utils.expand_command", expand),
            patch(
                "rovr.core.preview_container.subprocess.run", side_effect=run
            ) as process,
            patch("rovr.functions.cache._cache_path", return_value=str(cached)),
            patch(
                "rovr.functions.cache.load",
                side_effect=lambda *args: (
                    cached.read_bytes() if cached.exists() else None
                ),
            ),
            patch("rovr.functions.cache.save", side_effect=save),
            patch.object(preview, f"show_{preview_type}_preview", side_effect=render),
        ):
            await asyncio.to_thread(show)
            assert preview._current_file_path == (
                str(cached) if preview_type == "pdf" else str(source)
            )
            await asyncio.to_thread(show)
            process.assert_called_once()
            assert preview._is_pdf() == (preview_type == "pdf")


async def test_subprocess_error_is_rendered_as_literal_text() -> None:
    app = PreviewTestApp()
    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        preview._current_content = "Command ['helium', 'C:\\Users\\notso'] failed"
        token = preview._active_preview_token
        preview_token = preview.preview_token

        def show() -> None:
            context_token = preview_token.set(token)
            try:
                preview.mount_special_messages(mime=False)
            finally:
                preview_token.reset(context_token)

        await asyncio.to_thread(show)
        content = preview.query_one(Static).content
        assert isinstance(content, Content)
        assert content.plain == preview._current_content


async def test_call_from_thread_rejects_stale_preview() -> None:
    app = PreviewTestApp()

    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        current_token = preview._active_preview_token
        preview_token = preview.preview_token

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


async def test_hidden_mime_does_not_replace_newer_preview(tmp_path: Path) -> None:
    source = tmp_path / "file.txt"
    source.write_text("hello")
    started, release = Event(), Event()

    def get_mime(*args: Any) -> MimeResult:
        started.set()
        release.wait(2)
        return MimeResult("basic", "text/plain")

    app = PreviewTestApp()
    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        preview.add_class("hide")
        with (
            patch("rovr.core.preview_container.preview_utils.get_mime_type", get_mime),
            patch.object(preview, "_sync_mime") as sync_mime,
        ):
            preview.show_preview(str(source), source.stat().st_mtime)
            token = preview._active_preview_token
            try:
                assert await asyncio.to_thread(started.wait, 2)
                assert preview._active_preview_token is token
                preview._active_preview_token = object()
            finally:
                release.set()
            await asyncio.sleep(0.1)
            sync_mime.assert_not_called()


async def test_folder_preview_stops_loading_timer_on_cancellation(
    tmp_path: Path,
) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        preview = app.query_one(PreviewContainer)
        timer = Mock()
        preview_token = preview.preview_token

        def show() -> None:
            context_token = preview_token.set(preview._active_preview_token)
            try:
                preview.show_folder_preview(str(tmp_path))
            finally:
                preview_token.reset(context_token)

        with (
            patch.object(preview, "set_timer", return_value=timer),
            patch(
                "rovr.core.preview_container.path_utils.sync_get_cwd_object",
                side_effect=ExitNow,
            ),
            pytest.raises(ExitNow),
        ):
            await asyncio.to_thread(show)
        timer.stop.assert_called_once_with()


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
            patch("rovr.functions.cache.load", return_value=None),
            patch("rovr.functions.cache.save") as save,
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


async def test_stale_bat_line_count_stops_before_cache_access(tmp_path: Path) -> None:
    file = tmp_path / "large.txt"
    file.write_text("line\n" * 600, encoding="utf-8")
    app = PreviewTestApp()

    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        stale_token = preview._active_preview_token
        preview._active_preview_token = object()
        source = LazyTextLines(256, 256, lambda page: None)
        text_preview = WindowedTextPreview(source)

        with patch("rovr.functions.cache.load") as load:
            await asyncio.to_thread(
                preview._count_bat_lines,
                stale_token,
                text_preview,
                source,
                str(file),
                file.stat(),
                ("test", "bat"),
            )

        assert not load.called
        assert len(source) == 256


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
        preview_token = preview.preview_token

        def show_preview() -> None:
            context_token = preview_token.set(token)
            try:
                preview.show_normal_file_preview()
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.functions.cache.load", return_value=None),
            patch("rovr.functions.cache.save"),
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
        preview_token = preview.preview_token

        def show_preview() -> None:
            context_token = preview_token.set(token)
            try:
                preview.show_normal_file_preview()
            finally:
                preview_token.reset(context_token)

        with (
            patch("rovr.functions.cache.load", return_value=None),
            patch("rovr.functions.cache.save") as save,
        ):
            await asyncio.to_thread(show_preview)
        await pilot.pause()

        cached_content = save.call_args.args[4]
        assert cached_content == "first\n---\n(13 bytes ignored)"

        with (
            patch(
                "rovr.functions.cache.load",
                return_value=cached_content,
            ),
            patch("rovr.functions.cache.save") as save,
        ):
            await asyncio.to_thread(show_preview)
        assert not save.called


def test_truncated_multibyte_character_is_counted_as_ignored() -> None:
    assert _decode_text_preview("é".encode()[:1], truncated=True) == ("", 1)
