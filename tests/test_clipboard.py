from pathlib import Path

import pytest
from textual.worker import Worker

from rovr.app import Application


async def test_bulk_clipboard_preserves_selection_and_indices(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    old = (tmp_path / "old.txt").as_posix()
    items = [(tmp_path / f"file_{i}.txt").as_posix() for i in range(1000)]
    async with app.run_test(size=(143, 37)):
        await app.Clipboard.copy_to_clipboard([old]).wait()
        app.Clipboard.highlighted = 0
        await app.Clipboard.cut_to_clipboard(items, select="no").wait()
        assert [option.value.path for option in app.Clipboard.options] == items + [old]
        assert [value.path for value in app.Clipboard.selected] == [old]
        assert app.Clipboard.highlighted == 1000
        for index, option in enumerate(app.Clipboard.options):
            assert option.id is not None
            assert app.Clipboard.get_option_index(option.id) == index
            assert app.Clipboard._values[option.value] == index
        await app.Clipboard.copy_to_clipboard([items[10]], select="select").wait()
        assert app.Clipboard.option_count == 1001
        assert {value.path for value in app.Clipboard.selected} == {old, items[10]}


@pytest.mark.parametrize("operation", ["copy_to_clipboard", "cut_to_clipboard"])
@pytest.mark.asyncio
async def test_duplicate_items_do_not_select_existing_options(
    tmp_path: Path, operation: str
) -> None:
    existing = tmp_path / "existing.txt"
    duplicate = tmp_path / "duplicate.txt"
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        worker: Worker = app.Clipboard.copy_to_clipboard(
            [existing.as_posix()], select="no"
        )
        await worker.wait()

        worker = getattr(app.Clipboard, operation)([
            duplicate.as_posix(),
            duplicate.as_posix(),
        ])
        await worker.wait()

        assert [item.path for item in app.Clipboard.selected] == [duplicate.as_posix()]


@pytest.mark.asyncio
async def test_delete_from_clipboard(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        worker: Worker = app.Clipboard.copy_to_clipboard([file.as_posix()])
        await worker.wait()
        await pilot.pause()
        assert app.Clipboard.options[0].value.path == file.as_posix()
        file.unlink()
        worker: Worker = app.Clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 0


@pytest.mark.asyncio
async def test_clipboard_keeps_broken_symlink(tmp_path: Path) -> None:
    target = tmp_path / "missing.txt"
    link_path = tmp_path / "missing-link.txt"
    try:
        link_path.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink not supported: {exc}")

    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        worker: Worker = app.Clipboard.copy_to_clipboard([link_path.as_posix()])
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
        assert app.Clipboard.options[0].value.path == link_path.as_posix()

        worker = app.Clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
