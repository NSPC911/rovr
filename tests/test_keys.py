from pathlib import Path

import pytest

from rovr.app import Application
from rovr.screens import Dismissible

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
        assert app._active_key_contexts()[-1] == ("main", app.screen)
        assert app._key_namespaces()["file_list"] is app.file_list

        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.keys["lists"]["j"] = "noop"
        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.push_screen(Dismissible("Modal"))
        await pilot.pause()
        assert "main" not in {context for context, _ in app._active_key_contexts()}
