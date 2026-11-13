from pathlib import Path
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

from rovr.app import Application
from rovr.variables.constants import config

from .conftest import iter_until, workers_finished


@pytest.mark.asyncio
async def test_explicit_mode_stays_on_after_last_deselection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        opener = AsyncMock()
        monkeypatch.setattr(items, "file_selected_handler", opener)
        await items.action_toggle_visual()
        assert items.select_mode == "explicit"
        items.action_select()
        await workers_finished(pilot, items)
        items.action_select()
        await workers_finished(pilot, items)
        assert not items.selected
        assert items.select_mode == "explicit"
        await items.action_toggle_visual()
        assert items.select_mode is False
        assert app.tabWidget.active_tab is not None
        assert app.tabWidget.active_tab.session.selectMode is False
        opener.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("deselect_with", ["action_select", "action_toggle_all"])
async def test_implicit_mode_exits_when_last_item_is_deselected(
    tmp_path: Path, deselect_with: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        opener = AsyncMock()
        monkeypatch.setattr(items, "file_selected_handler", opener)
        await items.action_toggle_all()
        await iter_until(
            pilot, lambda: items.select_mode == "implicit" and bool(items.selected)
        )
        assert app.tabWidget.active_tab is not None
        assert app.tabWidget.active_tab.session.selectMode == "implicit"
        result = getattr(items, deselect_with)()
        if result is not None:
            await result
        await iter_until(pilot, lambda: items.select_mode is False)
        assert not items.selected
        assert app.tabWidget.active_tab.session.selectMode is False
        await workers_finished(pilot, items)
        opener.assert_not_awaited()


@pytest.mark.asyncio
async def test_normal_select_opens_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        opener = AsyncMock()
        monkeypatch.setattr(items, "file_selected_handler", opener)
        items.action_select()
        await iter_until(pilot, lambda: opener.await_count == 1)
        assert opener.await_args is not None
        assert Path(opener.await_args.args[0][0]) == tmp_path / "a"


@pytest.mark.asyncio
async def test_range_selection_enters_implicit_mode(tmp_path: Path) -> None:
    for name in ("a", "b"):
        (tmp_path / name).touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 2)
        items = app.file_list
        await items.action_select_cursor(1)
        assert items.select_mode == "implicit"
        assert len(items.selected) == 2
        assert items.highlighted == 1


@pytest.mark.asyncio
async def test_range_selection_does_not_scan_all_options(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 3)
        items = app.file_list
        await items.toggle_mode()
        with (
            patch.object(
                type(items), "selected_options", new_callable=PropertyMock
            ) as selected,
            patch.object(items, "get_selected_objects", new_callable=AsyncMock) as paths,
        ):
            selected.side_effect = AssertionError("scanned selected options")
            paths.side_effect = AssertionError("built selected paths")
            await items.action_select_down()
            await workers_finished(pilot, items)
            assert "2/3" in str(getattr(items.parent, "border_subtitle", ""))


@pytest.mark.asyncio
async def test_auto_select_disabled_does_not_enter_implicit_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").touch()
    monkeypatch.setitem(config["interface"], "allow_auto_select_mode", False)  # ty: ignore[invalid-argument-type]
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        await items.action_select_down()
        assert items.select_mode is False
        assert not items.selected


@pytest.mark.asyncio
async def test_range_at_boundary_does_not_enter_mode(tmp_path: Path) -> None:
    (tmp_path / "a").touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        await items.action_select_cursor(1)
        assert items.select_mode is False
        assert not items.selected


@pytest.mark.asyncio
async def test_implicit_mode_exits_if_auto_select_is_disabled_mid_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        opener = AsyncMock()
        monkeypatch.setattr(items, "file_selected_handler", opener)
        await items.action_toggle_all()
        await iter_until(
            pilot, lambda: items.select_mode == "implicit" and bool(items.selected)
        )
        monkeypatch.setitem(config["interface"], "allow_auto_select_mode", False)  # ty: ignore[invalid-argument-type]
        items.action_select()
        await workers_finished(pilot, items)
        await pilot.pause()
        assert items.select_mode is False
        opener.assert_not_awaited()


@pytest.mark.asyncio
async def test_exited_select_mode_on_tab_change(tmp_path: Path) -> None:
    from textual.widgets import Button

    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "file").touch()
    app = Application(startup_path=(tmp_path / "a").as_posix())
    async with app.run_test() as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 1)
        items = app.file_list
        await items.action_toggle_all()
        await pilot.pause()
        assert app.file_list.get_option_at_index(0).dir_entry.name == "file"
        await app.action_tab_new()
        await pilot.pause()
        assert app.file_list.get_option_at_index(0).dir_entry.name == "file"
        app.query_one("UpButton", Button).on_button_pressed()
        await pilot.pause(0.5)
        assert app.file_list.get_option_at_index(0).dir_entry.name == "a"
        (tmp_path / "a" / "file").unlink()
        await pilot.pause()
        app.action_tab_previous()
        await pilot.pause(0.5)
        assert app.file_list.get_option_at_index(0).disabled
        assert not app.file_list.select_mode
