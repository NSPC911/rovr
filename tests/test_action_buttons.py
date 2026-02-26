import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from textual.widgets import OptionList, SelectionList

from rovr.action_buttons import (
    CopyButton,
    CutButton,
    DeleteButton,
    NewItemButton,
    PasteButton,
    RenameItemButton,
    UnzipButton,
    ZipButton,
)
from rovr.app import Application


@pytest.mark.asyncio
async def test_copy_button(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )


@pytest.mark.asyncio
async def test_cut_button(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_copy_to_cut(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_cut_to_copy(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )


@pytest.mark.asyncio
async def test_paste_button(tmp_path: Path) -> None:
    from rovr.screens import PasteScreen

    open(tmp_path / "test_file.txt", "w").close()
    try:
        app = Application(startup_path=tmp_path.as_posix())
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(CopyButton)
            await pilot.pause()
            await pilot.click(PasteButton)
            await pilot.pause(1)
            assert isinstance(app.screen, PasteScreen)
            assert (
                app.screen
                .query_one("SpecialOptionList", OptionList)
                .get_option_at_index(0)
                .copy_or_cut
                == "copy"
            )
            await pilot.click("#no")
            await pilot.pause()
            await pilot.click(CutButton)
            await pilot.pause()
            await pilot.click(PasteButton)
            await pilot.pause(1)
            assert isinstance(app.screen, PasteScreen)
            assert (
                app.screen
                .query_one("SpecialOptionList", OptionList)
                .get_option_at_index(0)
                .copy_or_cut
                == "cut"
            )
    finally:
        os.chdir(Path("~").expanduser())


@pytest.mark.asyncio
async def test_delete_button(tmp_path: Path) -> None:
    from rovr.screens import DeleteFiles

    open(tmp_path / "test_file.txt", "w").close()
    try:
        app = Application(startup_path=tmp_path.as_posix())
        async with app.run_test(size=(143, 37)) as pilot:
            assert (
                app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
            )
            await pilot.click(DeleteButton)
            await pilot.pause()
            assert isinstance(app.screen, DeleteFiles)
            await pilot.click("#trash")
            # wait 2 seconds so you ensure watcher thread goes at least once
            # and updates the file list
            await pilot.pause(2)
            assert app.file_list.get_option_at_index(0).disabled
    finally:
        os.chdir(Path("~").expanduser())


@pytest.mark.asyncio
async def test_new_button() -> None:
    from rovr.screens import ModalInput

    temp_dir = TemporaryDirectory()
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(NewItemButton)
            await pilot.pause()
            assert isinstance(app.screen, ModalInput)
            await pilot.press(
                "t", "e", "s", "t", "_", "f", "i", "l", "e", ".", "t", "x", "t", "enter"
            )
            await pilot.pause(1)
            assert not isinstance(app.screen, ModalInput)
            assert (
                app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
            )
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()


@pytest.mark.asyncio
async def test_rename_button() -> None:
    from rovr.screens import ModalInput

    temp_dir = TemporaryDirectory()
    open(os.path.join(temp_dir.name, "test_file.txt"), "w").close()
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            assert (
                app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
            )
            await pilot.click(RenameItemButton)
            await pilot.pause()
            assert isinstance(app.screen, ModalInput)
            await pilot.press(
                "r",
                "e",
                "n",
                "a",
                "m",
                "e",
                "d",
                "_",
                "f",
                "i",
                "l",
                "e",
                ".",
                "t",
                "x",
                "t",
                "enter",
            )
            await pilot.pause(1)
            assert not isinstance(app.screen, ModalInput)
            assert (
                app.file_list.get_option_at_index(0).dir_entry.name
                == "renamed_file.txt"
            )
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()


@pytest.mark.asyncio
async def test_zip_button() -> None:
    from rovr.screens import ArchiveCreationScreen

    empty_dir = TemporaryDirectory()
    try:
        app = Application(startup_path=empty_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(ZipButton)
            await pilot.pause()
            assert not isinstance(app.screen, ArchiveCreationScreen)
    finally:
        os.chdir(Path("~").expanduser())
        empty_dir.cleanup()

    temp_dir = TemporaryDirectory()
    open(os.path.join(temp_dir.name, "test_file.txt"), "w").close()
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(ZipButton)
            await pilot.pause(1)
            assert isinstance(app.screen, ArchiveCreationScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, ArchiveCreationScreen)
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()


@pytest.mark.asyncio
async def test_zip_button_creates_archive() -> None:
    from rovr.screens import ArchiveCreationScreen

    temp_dir = TemporaryDirectory()
    open(os.path.join(temp_dir.name, "test_file.txt"), "w").close()
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(ZipButton)
            await pilot.pause(1)
            assert isinstance(app.screen, ArchiveCreationScreen)
            await pilot.press("enter")
            await pilot.pause(1)
            assert not isinstance(app.screen, ArchiveCreationScreen)
            assert any(f.endswith(".zip") for f in os.listdir(temp_dir.name))
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()


@pytest.mark.asyncio
async def test_unzip_button() -> None:
    import zipfile

    from rovr.screens import ModalInput

    empty_dir = TemporaryDirectory()
    try:
        app = Application(startup_path=empty_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(UnzipButton)
            await pilot.pause()
            assert not isinstance(app.screen, ModalInput)
    finally:
        os.chdir(Path("~").expanduser())
        empty_dir.cleanup()

    temp_dir = TemporaryDirectory()
    zip_path = os.path.join(temp_dir.name, "test_archive.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "hello")
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(UnzipButton)
            await pilot.pause(1)
            assert isinstance(app.screen, ModalInput)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, ModalInput)
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()


@pytest.mark.asyncio
async def test_unzip_button_extracts_archive() -> None:
    import zipfile

    from rovr.screens import ModalInput

    temp_dir = TemporaryDirectory()
    zip_path = os.path.join(temp_dir.name, "test_archive.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "hello")
    try:
        app = Application(startup_path=temp_dir.name)
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            await pilot.click(UnzipButton)
            await pilot.pause(1)
            assert isinstance(app.screen, ModalInput)
            await pilot.press("enter")
            await pilot.pause(1)
            assert not isinstance(app.screen, ModalInput)
            assert os.path.isdir(os.path.join(temp_dir.name, "test_archive"))
    finally:
        os.chdir(Path("~").expanduser())
        temp_dir.cleanup()
