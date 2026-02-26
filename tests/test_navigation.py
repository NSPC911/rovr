import os
from pathlib import Path

import pytest

from rovr.app import Application
from rovr.navigation_widgets import BackButton


@pytest.mark.asyncio
async def test_nav(tmp_path: Path) -> None:
    app = Application()
    os.mkdir(tmp_path / "test")
    open(tmp_path / "test" / "file.txt", "w").close()
    try:
        app = Application(startup_path=tmp_path.as_posix())
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            assert (nested_thing := app.file_list.get_option_at_index(0))
            assert (
                nested_thing.dir_entry.is_dir()
                and nested_thing.dir_entry.name == Path(tmp_path / "test").name
            )
            app.file_list.select(app.file_list.get_option_at_index(0))
            await pilot.pause()
            assert (option := app.file_list.get_option_at_index(0))
            assert option.dir_entry.is_file() and option.dir_entry.name == "file.txt"
            await pilot.click(BackButton)
            await pilot.pause()
            assert (option := app.file_list.get_option_at_index(0))
    finally:
        os.chdir(Path("~").expanduser())


@pytest.mark.asyncio
async def test_history_nav(tmp_path: Path) -> None:
    app = Application()
    os.mkdir(tmp_path / "test1")
    try:
        app = Application(startup_path=tmp_path.as_posix())
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            assert (
                app.query_one("BackButton").disabled
                and app.query_one("ForwardButton").disabled
                and (not app.query_one("UpButton").disabled)
            )
            await pilot.click("UpButton")
            await pilot.pause()
            assert (
                app.query_one("ForwardButton").disabled
                and (not app.query_one("BackButton").disabled)
                and (not app.query_one("UpButton").disabled)
            )
            await pilot.click("BackButton")
            await pilot.pause()
            assert (
                app.query_one("BackButton").disabled
                and (not app.query_one("ForwardButton").disabled)
                and (not app.query_one("UpButton").disabled)
            )
            await pilot.click("ForwardButton")
            await pilot.pause()
            assert (
                app.query_one("ForwardButton").disabled
                and (not app.query_one("BackButton").disabled)
                and (not app.query_one("UpButton").disabled)
            )
    finally:
        os.chdir(Path("~").expanduser())
