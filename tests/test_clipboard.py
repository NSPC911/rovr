from pathlib import Path

import pytest
from textual.worker import Worker

from rovr.app import Application


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
