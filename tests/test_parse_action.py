from pathlib import Path

import pytest

from rovr.app import Application


@pytest.mark.asyncio
async def test_simple_action_exists(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        result = app.parse_action(app.file_list, "cursor_down")
        assert result is not None
        assert result.target is app.file_list
        assert result.condition is None


@pytest.mark.asyncio
async def test_simple_action_not_found(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        result = app.parse_action(app.file_list, "nonexistent_action")
        assert result is None


@pytest.mark.asyncio
async def test_malformed_colon_only(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        result = app.parse_action(app.file_list, "FileList:cursor_down")
        assert result is None


@pytest.mark.asyncio
async def test_malformed_colon_before_equals(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        result = app.parse_action(app.file_list, "FileList:focused=cursor_down")
        assert result is None


@pytest.mark.asyncio
async def test_conditioned_focused_when_focused(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.set_focus(app.file_list)
        await pilot.pause()
        result = app.parse_action(app.file_list, "focused=FileList:cursor_down")
        assert result is not None
        assert result.condition == "focused"


@pytest.mark.asyncio
async def test_conditioned_focused_when_not_focused(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        # focus something other than FileList
        app.set_focus(None)
        await pilot.pause()
        result = app.parse_action(app.file_list, "focused=FileList:cursor_down")
        assert result is None


@pytest.mark.asyncio
async def test_conditioned_blurred_when_not_focused(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.set_focus(None)
        await pilot.pause()
        result = app.parse_action(app.file_list, "blurred=FileList:cursor_down")
        assert result is not None
        assert result.condition == "blurred"


@pytest.mark.asyncio
async def test_conditioned_blurred_when_focused(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.set_focus(app.file_list)
        await pilot.pause()
        result = app.parse_action(app.file_list, "blurred=FileList:cursor_down")
        assert result is None


@pytest.mark.asyncio
async def test_conditioned_invalid_state(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        result = app.parse_action(app.file_list, "hover=FileList:cursor_down")
        assert result is None


@pytest.mark.asyncio
async def test_conditioned_selector_no_match(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        result = app.parse_action(
            app.file_list, "focused=NonExistentWidget:cursor_down"
        )
        assert result is None


@pytest.mark.asyncio
async def test_conditioned_focus_within(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.set_focus(app.file_list)
        await pilot.pause()
        # FileList is inside the app, so the app screen has focus-within
        result = app.parse_action(
            app, "focus-within=FileList:focus_toggle_pinned_sidebar"
        )
        assert result is not None
        assert result.condition == "focus-within"
