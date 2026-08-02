from pathlib import Path

import pytest

from rovr.app import Application

from .conftest import iter_until


@pytest.mark.asyncio
async def test_chooser_quit_does_not_write_selection(tmp_path: Path) -> None:
    selected_file = tmp_path / "file.txt"
    selected_file.touch()
    chooser_file = tmp_path / "chooser-output"
    app = Application(tmp_path.as_posix(), chooser_file=chooser_file.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: bool(app.file_list.options))
        app.action_quit()
        await pilot.pause()

    assert not chooser_file.exists()


@pytest.mark.asyncio
async def test_chooser_open_writes_highlighted_file(tmp_path: Path) -> None:
    selected_file = tmp_path / "file.txt"
    selected_file.touch()
    chooser_file = tmp_path / "chooser-output"
    app = Application(tmp_path.as_posix(), chooser_file=chooser_file.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: bool(app.file_list.options))
        await pilot.press("enter")
        await pilot.pause()

    assert chooser_file.read_text(encoding="utf-8") == selected_file.as_posix()


@pytest.mark.asyncio
async def test_chooser_open_writes_visual_selection(tmp_path: Path) -> None:
    selected_files = [tmp_path / f"file-{index}.txt" for index in range(3)]
    for selected_file in selected_files:
        selected_file.touch()
    chooser_file = tmp_path / "chooser-output"
    app = Application(tmp_path.as_posix(), chooser_file=chooser_file.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: len(app.file_list.options) == 3)
        await app.file_list.toggle_mode()
        app.file_list.select(app.file_list.get_option_at_index(0))
        app.file_list.select(app.file_list.get_option_at_index(2))
        await pilot.press("enter")
        await pilot.pause()

    assert chooser_file.read_text(encoding="utf-8").splitlines() == [
        selected_files[0].as_posix(),
        selected_files[2].as_posix(),
    ]
