import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from rovr.app import Application
from rovr.navigation_widgets import BackButton


@pytest.mark.asyncio
async def test_nav() -> None:
    app = Application()
    temp_dir = TemporaryDirectory()
    temp_temp_dir = TemporaryDirectory(dir=temp_dir.name)
    open(os.path.join(temp_temp_dir.name, "test.txt"), "w").close()
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            assert (nested_thing := app.file_list.get_option_at_index(0))
            assert (
                nested_thing.dir_entry.is_dir()
                and nested_thing.dir_entry.name == Path(temp_temp_dir.name).name
            )
            app.file_list.select(app.file_list.get_option_at_index(0))
            await pilot.pause()
            assert (option := app.file_list.get_option_at_index(0))
            assert option.dir_entry.is_file() and option.dir_entry.name == "test.txt"
            await pilot.click(BackButton)
            await pilot.pause()
            assert (option := app.file_list.get_option_at_index(0))
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()
        temp_temp_dir.cleanup()
