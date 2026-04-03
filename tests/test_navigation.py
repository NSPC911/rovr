import os
from pathlib import Path

import pytest
from textual import events

from rovr.app import Application
from rovr.components import PopupOptionList, SearchInput
from rovr.navigation_widgets import BackButton

from .conftest import iter_until, workers_finished


@pytest.mark.asyncio
async def test_nav(tmp_path: Path) -> None:
    os.mkdir(tmp_path / "test")
    open(tmp_path / "test" / "file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.get_option_at_index(0))
        assert (nested_thing := app.file_list.get_option_at_index(0))
        assert (
            nested_thing.dir_entry.is_dir()
            and nested_thing.dir_entry.name == Path(tmp_path / "test").name
        )
        app.file_list.select(app.file_list.get_option_at_index(0))
        # honestly no better way to do that
        await iter_until(
            pilot, lambda: app.file_list.get_option_at_index(0).dir_entry.is_file()
        )
        assert app.file_list.get_option_at_index(0).dir_entry.name == "file.txt"
        await pilot.click(BackButton)
        await iter_until(
            pilot, lambda: app.file_list.get_option_at_index(0).dir_entry.is_dir()
        )


@pytest.mark.asyncio
async def test_history_nav(tmp_path: Path) -> None:
    os.mkdir(tmp_path / "test1")
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(
            pilot,
            lambda: (
                app.query_one("BackButton").disabled
                and app.query_one("ForwardButton").disabled
                and (not app.query_one("UpButton").disabled)
            ),
        )
        await pilot.click("UpButton")
        await iter_until(
            pilot,
            lambda: (
                app.query_one("ForwardButton").disabled
                and (not app.query_one("BackButton").disabled)
                and (not app.query_one("UpButton").disabled)
            ),
        )
        await pilot.click("BackButton")
        await iter_until(
            pilot,
            lambda: (
                app.query_one("BackButton").disabled
                and (not app.query_one("ForwardButton").disabled)
                and (not app.query_one("UpButton").disabled)
            ),
        )
        await pilot.click("ForwardButton")
        await iter_until(
            pilot,
            lambda: (
                app.query_one("ForwardButton").disabled
                and (not app.query_one("BackButton").disabled)
                and (not app.query_one("UpButton").disabled)
            ),
        )


@pytest.mark.asyncio
async def test_tab_highlight(tmp_path: Path) -> None:
    for i in range(10):
        open(tmp_path / f"file{i}", "w").close()

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
        await iter_until(
            pilot,
            lambda: (
                app.file_list.highlighted_option.dir_entry.name == name
                and app.file_list.highlighted == index
            ),
        )


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
        await iter_until(pilot, lambda: app.tabWidget.active_tab)
        await workers_finished(pilot, app.file_list)

        assert app.file_list.input.value == "file"
        assert app.tabWidget.active_tab.session.search == "file"
        assert app.file_list.highlighted_option.dir_entry.name == name
        assert app.file_list.highlighted == index


@pytest.mark.asyncio
async def test_tab_search_clears_on_navigation(tmp_path: Path) -> None:
    os.mkdir(tmp_path / "nested")
    open(tmp_path / "file0.txt", "w").close()

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.options)
        app.file_list.input.value = "file"
        await pilot.pause()
        assert app.tabWidget.active_tab.session.search == "file"

        app.cd((tmp_path / "nested").as_posix())
        await workers_finished(pilot, app.file_list)
        await pilot.pause()

        assert app.file_list.input.value == ""
        assert app.tabWidget.active_tab.session.search == ""


@pytest.mark.asyncio
async def test_sidebar_search_does_not_override_tab_search(tmp_path: Path) -> None:
    for i in range(3):
        open(tmp_path / f"file{i}.txt", "w").close()

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.options)
        app.file_list.input.value = "file"
        await pilot.pause()
        assert app.tabWidget.active_tab.session.search == "file"

        sidebar_search = app.query_one("#pinned_sidebar_container").query_one(
            SearchInput
        )
        sidebar_search.value = "home"
        await pilot.pause()

        assert app.tabWidget.active_tab.session.search == "file"


@pytest.mark.asyncio
async def test_tab_multiselection(tmp_path: Path) -> None:
    for i in range(10):
        open(tmp_path / f"file{i}", "w").close()

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
        await workers_finished(pilot, app.file_list)

        assert app.file_list.select_mode_enabled
        indexes = [0, 2, 4, 7]
        for selected_id in app.file_list.selected:
            assert app.file_list.get_option_index(selected_id) in indexes
            indexes.remove(app.file_list.get_option_index(selected_id))


@pytest.mark.asyncio
async def test_preview_bypass_folder(tmp_path: Path) -> None:
    os.makedirs(tmp_path / "folder" / "subfolder")
    open(tmp_path / "folder" / "file.txt", "w").close()
    open(tmp_path / "folder" / "subfolder" / "subfoldered-file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        assert app.file_list.highlighted == 0
        await workers_finished(pilot, app.query_one("PreviewContainer"))
        app.query_one("PreviewContainer").query_one("FileList").highlighted = 0
        await pilot.pause()
        app.query_one("PreviewContainer").query_one("FileList").action_select()
        await pilot.pause()
        await workers_finished(pilot, app.file_list)
        assert app.file_list.highlighted == 0
        assert app.file_list.highlighted_option.dir_entry.name == "subfoldered-file.txt"


@pytest.mark.asyncio
async def test_right_click_empty(tmp_path: Path) -> None:
    os.makedirs(tmp_path / "folder")
    app = Application(startup_path=(tmp_path / "folder").as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot._post_mouse_events(
            [events.MouseDown, events.MouseUp, events.Click],
            app.file_list,
            (8, 0),
            button=3,
            shift=False,
            meta=False,
            control=False,
            times=1,
        )
        await pilot.pause()
        assert all(
            option.disabled
            for option in app.query_one(
                "FileListRightClickOptionList", PopupOptionList
            ).options
        )
