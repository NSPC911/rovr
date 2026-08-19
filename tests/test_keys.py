from pathlib import Path

import pytest

from rovr.action_buttons import CopyButton
from rovr.action_buttons.sort_order import SortOrderButton
from rovr.app import Application
from rovr.screens import Dismissible
from rovr.state_manager import StateManager

from .conftest import iter_until


@pytest.mark.asyncio
async def test_contextual_key_dispatch(tmp_path: Path) -> None:
    (tmp_path / "a").touch()
    (tmp_path / "b").touch()
    app = Application(startup_path=tmp_path.as_posix())
    app.keys = {"lists": {"j": "cursor(1)"}}

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 2)
        app.file_list.focus()
        app.file_list.highlighted = 0

        assert [context for context, _ in app._active_key_contexts()] == [
            "file_list",
            "lists",
            "main",
        ]
        assert app._active_key_contexts()[-1] == ("main", app)
        assert app._key_namespaces()["file_list"] is app.file_list
        assert app._key_namespaces()["copy"] is app.query_one(CopyButton)
        assert app._key_namespaces()["sort_order"] is app.query_one(SortOrderButton)

        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.keys["lists"]["j"] = "noop"
        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.keys["file_list"] = {"s": "sort_order.extension(True)"}
        await pilot.press("s")
        assert app.query_one(StateManager).get_sort_prefs() == ("extension", True)

        state_manager = app.query_one(StateManager)
        pinned_sidebar_visible = state_manager.pinned_sidebar_visible
        app.keys = {"main": {"S": "toggle_pinned_sidebar"}}
        await pilot.press("S")
        assert state_manager.pinned_sidebar_visible is not pinned_sidebar_visible

        app.push_screen(Dismissible("Modal"))
        await pilot.pause()
        assert "main" not in {context for context, _ in app._active_key_contexts()}
