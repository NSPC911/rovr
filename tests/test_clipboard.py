from pathlib import Path

import pytest
from textual.style import Style
from textual.worker import Worker

from rovr.app import Application
from rovr.footer.clipboard_container import Clipboard

from .conftest import iter_until

# no need to check deduplication, thats done in test_action_buttons


@pytest.mark.asyncio
async def test_delete_from_clipboard(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        clipboard = app.query_one(Clipboard)
        worker: Worker = clipboard.copy_to_clipboard([file.as_posix()])
        await worker.wait()
        await pilot.pause()
        assert clipboard.options[0].value.path == file.as_posix()
        file.unlink()
        worker: Worker = clipboard.check_clipboard_existence()
        await worker.wait()
        await pilot.pause()
        assert len(clipboard.options) == 0


@pytest.mark.asyncio
async def test_dimming(tmp_path: Path) -> None:
    def check_dim(style: str | Style) -> bool:
        if isinstance(style, str):
            style = Style.parse(style)
        return style.dim or False

    file = tmp_path / "file.txt"
    file.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        clipboard = app.query_one(Clipboard)
        await pilot.click("CutButton")
        await iter_until(
            pilot,
            lambda: (
                worker
                for worker in app.workers
                if worker.node == clipboard and worker.is_finished
            ),
        )
        # get first option's dimness
        assert check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        clipboard.highlighted = 0
        await pilot.pause()
        clipboard.action_select()
        await pilot.pause(0.5)
        # once unselected, the dimness should be gone
        assert not check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        clipboard.action_select()
        await pilot.pause(0.5)
        await pilot.click("CopyButton")
        await iter_until(
            pilot,
            lambda: (
                worker
                for worker in app.workers
                if (worker.node == clipboard or worker.node == app.file_list)
                and worker.is_finished
            ),
        )
        # copying should not cause dimness
        assert not check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        # then retry cutting, should cause dimness again
        await pilot.click("CutButton")
        await pilot.pause()
        await iter_until(
            pilot,
            lambda: (
                worker
                for worker in app.workers
                if (worker.node == clipboard or worker.node == app.file_list)
                and worker.is_finished
            ),
        )
        assert check_dim(app.file_list.options[0]._prompt.spans[-1].style)
