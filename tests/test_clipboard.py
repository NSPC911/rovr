from pathlib import Path

import pytest
from textual.worker import Worker

from rovr.app import Application

# no need to check deduplication, thats done in test_action_buttons


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

        worker = app.Clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
