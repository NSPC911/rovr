from pathlib import Path

import pytest
from textual.worker import Worker

from rovr.app import Application


async def test_bulk_clipboard_preserves_active_block(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    old = (tmp_path / "old.txt").as_posix()
    items = [(tmp_path / f"file_{i}.txt").as_posix() for i in range(1000)]
    async with app.run_test(size=(143, 37)):
        await app.Clipboard.copy_to_clipboard([old]).wait()
        app.Clipboard.index = 0
        await app.Clipboard.cut_to_clipboard(items, select=False).wait()
        assert [block.paths for block in app.Clipboard.options] == [tuple(items), (old,)]
        assert app.Clipboard.selected == ("copy", [old])
        assert app.Clipboard.index == 1
        await app.Clipboard.copy_to_clipboard([items[10]], select=True).wait()
        assert len(app.Clipboard.options) == 3
        assert app.Clipboard.selected == ("copy", [items[10]])


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
            [existing.as_posix()], select=False
        )
        await worker.wait()

        worker = getattr(app.Clipboard, operation)([
            duplicate.as_posix(),
            duplicate.as_posix(),
        ])
        await worker.wait()

        assert app.Clipboard.selected == (
            operation.removesuffix("_to_clipboard"),
            [duplicate.as_posix()],
        )


@pytest.mark.asyncio
async def test_clipboard_focus_initializes_cursor(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await app.Clipboard.copy_to_clipboard(
            [(tmp_path / "file.txt").as_posix()], select=False
        ).wait()

        app.Clipboard.focus()
        await pilot.pause()

        assert app.Clipboard.index == 0
        assert app.Clipboard.options[0].highlighted
        assert app.Clipboard.selected == (None, [])

        app.Clipboard.set_index(0)
        app.Clipboard.set_index(None)
        app.file_list.focus()
        app.Clipboard.focus()
        await pilot.pause()

        assert app.Clipboard.index == 0
        assert app.Clipboard.selected == (None, [])
        assert app.Clipboard.paste_button.disabled


@pytest.mark.asyncio
async def test_new_block_clears_old_cursor(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        await app.Clipboard.copy_to_clipboard([
            (tmp_path / "first.txt").as_posix()
        ]).wait()
        old = app.Clipboard.options[0]

        await app.Clipboard.copy_to_clipboard([
            (tmp_path / "second.txt").as_posix()
        ]).wait()
        new = app.Clipboard.options[0]

        assert new.highlighted
        assert not old.highlighted

        app.Clipboard.action_cursor_down()
        assert old.highlighted
        assert not new.highlighted

        app.Clipboard.action_cursor_up()
        assert new.highlighted
        assert not old.highlighted


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
        assert app.Clipboard.options[0].paths == (file.as_posix(),)
        file.unlink()
        worker: Worker = app.Clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 0


@pytest.mark.asyncio
async def test_removing_active_block_clears_selection(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        await app.Clipboard.copy_to_clipboard([str(tmp_path / "file.txt")]).wait()

        await app.Clipboard.remove_block(0)

        assert app.Clipboard.selected == (None, [])
        assert app.Clipboard.paste_button.disabled


@pytest.mark.asyncio
async def test_clipboard_removes_missing_paths_from_block(tmp_path: Path) -> None:
    existing = tmp_path / "existing.txt"
    missing = tmp_path / "missing.txt"
    existing.touch()
    missing.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await app.Clipboard.copy_to_clipboard([
            existing.as_posix(),
            missing.as_posix(),
        ]).wait()
        missing.unlink()

        await app.Clipboard.check_clipboard_existence().wait()
        await pilot.pause()

        assert app.Clipboard.options[0].paths == (existing.as_posix(),)
        assert app.Clipboard.selected == ("copy", [existing.as_posix()])


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
        assert app.Clipboard.options[0].paths == (link_path.as_posix(),)

        worker = app.Clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
