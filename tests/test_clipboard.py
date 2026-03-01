from pathlib import Path

import pytest
from textual.style import Style
from textual.worker import Worker

from rovr.app import Application
from rovr.footer.clipboard_container import Clipboard

# no need to check deduplication, thats done in test_action_buttons


@pytest.mark.asyncio
async def test_delete_from_clipboard(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test() as pilot:
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
    async with app.run_test() as pilot:
        await pilot.pause()
        clipboard = app.query_one(Clipboard)
        await pilot.click("CutButton")
        await pilot.pause()
        # get first option's dimness
        assert check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        clipboard.highlighted = 0
        await pilot.pause()
        clipboard.action_select()
        await pilot.pause(1)
        # once unselected, the dimness should be gone
        assert not check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        clipboard.action_select()
        await pilot.pause(1)
        await pilot.click("CopyButton")
        await pilot.pause()
        # copying should not cause dimness
        assert not check_dim(app.file_list.options[0]._prompt.spans[-1].style)
        # then retry cutting, should cause dimness again
        await pilot.click("CutButton")
        await pilot.pause()
        assert check_dim(app.file_list.options[0]._prompt.spans[-1].style)
