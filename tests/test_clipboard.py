from pathlib import Path

import pytest
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
    file = tmp_path / "file.txt"
    file.touch()
    app = Application(tmp_path.as_posix())
    async with app.run_test() as pilot:
        await pilot.pause()
        clipboard = app.query_one(Clipboard)
        await pilot.click("CutButton")
        await pilot.pause()
        # get first option's dimness
        assert app.screen.get_style_at(
            app.file_list.region.top_right.x - app.file_list.region.size.width,
            app.file_list.region.top_right.y,
        ).dim
        clipboard.highlighted = 0
        await pilot.pause()
        clipboard.action_select()
        await pilot.pause(1)
        # once unselected, the dimness should be gone
        assert not app.screen.get_style_at(
            app.file_list.region.top_right.x - app.file_list.region.size.width,
            app.file_list.region.top_right.y,
        ).dim
        clipboard.action_select()
        await pilot.pause(1)
        await pilot.click("CopyButton")
        await pilot.pause()
        # copying should not cause dimness
        assert not app.screen.get_style_at(
            app.file_list.region.top_right.x - app.file_list.region.size.width,
            app.file_list.region.top_right.y,
        ).dim
