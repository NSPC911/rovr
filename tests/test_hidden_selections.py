from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import AsyncMock

import pytest

import rovr.app
from rovr.action_buttons import rename_item_button
from rovr.action_buttons.rename_item_button import RenameItemButton
from rovr.app import Application
from rovr.functions.path import normalise
from rovr.functions.utils import expand_command

from .conftest import iter_until, workers_finished


@pytest.mark.asyncio
async def test_hidden_selections_are_counted_and_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("apple pie", "banana", "cherry tart"):
        (tmp_path / name).touch()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 3)
        await workers_finished(pilot, app.file_list)
        items = app.file_list
        search = items.input
        await items.toggle_mode()
        items.select_all()
        search.value = "banana"
        await workers_finished(pilot, search)
        assert items.option_count == 1
        assert "3/3" in str(items.parent.border_subtitle)

        items.deselect(items.get_option_at_index(0))
        await workers_finished(pilot, items)
        expected = [
            str(normalise(str(tmp_path / name))) for name in ("apple pie", "cherry tart")
        ]
        assert await items.get_selected_objects() == expected
        assert "2/3" in str(items.parent.border_subtitle)
        expanded = await expand_command(app, ["hx", "%s"])
        assert expanded == ["hx", *expected]

        opener = AsyncMock()
        monkeypatch.setattr(items, "file_selected_handler", opener)
        await items.action_open()
        opener.assert_awaited_once_with(expected)

        search.value = "no-matching-files"
        await workers_finished(pilot, search)
        assert await items.get_selected_objects() == expected
        assert "2/3" in str(items.parent.border_subtitle)
        opener.reset_mock()
        await items.action_open()
        opener.assert_awaited_once_with(expected)

        search.clear()
        await workers_finished(pilot, search)
        assert await items.get_selected_objects() == expected
        search.value = "banana"
        await workers_finished(pilot, search)
        await items.toggle_mode()
        assert "1/1" in str(items.parent.border_subtitle)
        search.clear()
        await workers_finished(pilot, search)
        assert not items.selected
        assert not search.selected


@pytest.mark.asyncio
@pytest.mark.parametrize("highlighted", [None, 0])
async def test_bulk_rename_with_no_visible_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, highlighted: int | None
) -> None:
    for name in ("apple", "banana"):
        (tmp_path / name).write_text(name)

    def edit_names(app: Application, command: str, **kwargs: object) -> CompletedProcess:
        names = Path(command)
        lines = names.read_text(encoding="utf-8").splitlines()
        assert [line.split("➔")[-1].strip() for line in lines] == ["apple", "banana"]
        names.write_text(
            "\n".join(line.rstrip() + "-new" for line in lines), encoding="utf-8"
        )
        return CompletedProcess(command, 0)

    monkeypatch.setattr(rename_item_button, "command", lambda editor, filename: filename)
    monkeypatch.setattr(rovr.app, "run_command", edit_names)
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 2)
        await workers_finished(pilot, app.file_list)
        items = app.file_list
        await items.toggle_mode()
        items.select_all()
        items.input.value = "no-matching-files"
        await workers_finished(pilot, items.input)
        items.highlighted = highlighted
        await app.query_one(RenameItemButton).on_button_pressed().wait()
        assert not (tmp_path / "apple").exists()
        assert not (tmp_path / "banana").exists()
        assert (tmp_path / "apple-new").read_text() == "apple"
        assert (tmp_path / "banana-new").read_text() == "banana"
        assert items.highlighted_option.dir_entry.name == "apple-new"
