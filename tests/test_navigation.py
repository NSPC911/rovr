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


@pytest.mark.asyncio
async def test_history_nav(tmp_path: Path) -> None:
    app = Application()
    os.mkdir(tmp_path / "test1")
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


@pytest.mark.asyncio
async def test_tab_highlight(tmp_path: Path) -> None:
    import string
    from random import choices

    for _ in range(10):
        open(tmp_path / "".join(choices(string.ascii_letters, k=10)), "w").close()

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.file_list.highlighted = 5
        await pilot.pause()
        (name, index) = (
            app.file_list.highlighted_option.dir_entry.name,
            app.file_list.highlighted,
        )
        await app.tabWidget.add_tab("")
        await pilot.pause()
        app.tabWidget.action_next_tab()
        await pilot.pause()

        assert app.file_list.highlighted_option.dir_entry.name == name
        assert app.file_list.highlighted == index


@pytest.mark.asyncio
async def test_tab_search(tmp_path: Path) -> None:
    for i in range(10):
        open(tmp_path / f"file{i}.txt", "w").close()

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.file_list.highlighted = 5
        await pilot.pause()
        app.file_list.input.value = "file"
        (name, index) = (
            app.file_list.highlighted_option.dir_entry.name,
            app.file_list.highlighted,
        )
        await app.tabWidget.add_tab("")
        await pilot.pause()
        app.tabWidget.action_next_tab()
        await pilot.pause(1)

        assert app.file_list.input.value == "file"
        assert app.file_list.highlighted_option.dir_entry.name == name
        assert app.file_list.highlighted == index


@pytest.mark.asyncio
async def test_tab_multiselection(tmp_path: Path) -> None:
    import string
    from random import choices

    for _ in range(10):
        open(tmp_path / "".join(choices(string.ascii_letters, k=10)), "w").close()

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        app.file_list.highlighted = 5
        await pilot.pause()
        await app.file_list.toggle_mode()
        for index in [2, 4, 7, 0]:
            app.file_list.select(app.file_list.get_option_at_index(index))
        await app.tabWidget.add_tab("")
        await pilot.pause()
        app.tabWidget.action_next_tab()
        await pilot.pause()

        assert app.file_list.select_mode_enabled
        indexes = [0, 2, 4, 7]
        for selected_id in app.file_list.selected:
            assert app.file_list.get_option_index(selected_id) in indexes
            indexes.remove(app.file_list.get_option_index(selected_id))
