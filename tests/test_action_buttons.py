import os
from pathlib import Path

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
from rovr.action_buttons.sort_order import (
    SortOrderButton,
    SortOrderPopup,
)
from rovr.app import Application
from rovr.state_manager import StateManager

from .conftest import iter_until


@pytest.mark.asyncio
async def test_copy_button(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
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
        assert len(app.Clipboard.options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
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
        assert len(app.Clipboard.options) == 1
        assert (
            app
            .query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_cut_to_copy(tmp_path: Path) -> None:
    open(tmp_path / "test_file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.Clipboard.options) == 1
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
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        await pilot.click(PasteButton)
        await iter_until(pilot, lambda: isinstance(app.screen, PasteScreen))
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
        await iter_until(pilot, lambda: isinstance(app.screen, PasteScreen))
        assert (
            app.screen
            .query_one("SpecialOptionList", OptionList)
            .get_option_at_index(0)
            .copy_or_cut
            == "cut"
        )


@pytest.mark.asyncio
async def test_delete_button(tmp_path: Path) -> None:
    from rovr.footer.process_container import ProcessContainer, ProgressBarContainer
    from rovr.screens import DeleteFiles

    open(tmp_path / "test_file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        assert app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
        await pilot.click(DeleteButton)
        await pilot.pause()
        assert isinstance(app.screen, DeleteFiles)
        await pilot.click("#trash")
        await iter_until(pilot, lambda: not isinstance(app.screen, DeleteFiles))
        await iter_until(
            pilot,
            lambda: (
                app
                .query_one(ProcessContainer)
                .query(ProgressBarContainer)
                .first()
                .progress_bar.percentage
                == 1
            ),
        )
        worker = app.cd(tmp_path.as_posix(), add_to_history=False)
        assert worker is not None
        await worker.wait()
        await pilot.pause()
        assert app.file_list.get_option_at_index(0).disabled


@pytest.mark.asyncio
async def test_move_and_delete_broken_symlink(tmp_path: Path) -> None:
    from os import path

    from rovr.footer.process_container import ProcessContainer

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    link = source / "broken-link"
    try:
        link.symlink_to(source / "missing")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink not supported: {exc}")

    app = Application(startup_path=source.as_posix())
    async with app.run_test(size=(143, 37)):
        process_container = app.query_one(ProcessContainer)
        worker = process_container.paste_items(
            copied=[], has_cut=[link.as_posix()], dest=destination.as_posix()
        )
        await worker.wait()

        moved_link = destination / link.name
        assert not path.lexists(link)
        assert path.lexists(moved_link)

        worker = process_container.delete_files([moved_link.as_posix()])
        await worker.wait()
        assert not path.lexists(moved_link)


@pytest.mark.asyncio
async def test_new_button(tmp_path: Path) -> None:
    from rovr.screens import ModalInput

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(NewItemButton)
        await pilot.pause()
        assert isinstance(app.screen, ModalInput)
        await pilot.press(
            "t", "e", "s", "t", "_", "f", "i", "l", "e", ".", "t", "x", "t", "enter"
        )
        await iter_until(pilot, lambda: not isinstance(app.screen, ModalInput))
        await iter_until(
            pilot,
            lambda: (
                app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
            ),
        )
        assert app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"


@pytest.mark.asyncio
async def test_rename_button(tmp_path: Path) -> None:
    from rovr.screens import ModalInput

    open(tmp_path / "test_file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        assert app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
        await pilot.click(RenameItemButton)
        await iter_until(pilot, lambda: isinstance(app.screen, ModalInput))
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
        await iter_until(pilot, lambda: not isinstance(app.screen, ModalInput))
        await iter_until(
            pilot,
            lambda: (
                app.file_list.get_option_at_index(0).dir_entry.name
                == "renamed_file.txt"
            ),
        )
        assert app.file_list.get_option_at_index(0).dir_entry.name == "renamed_file.txt"


@pytest.mark.asyncio
async def test_zip_button(tmp_path: Path) -> None:
    from rovr.screens import ArchiveCreationScreen

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(ZipButton)
        await pilot.pause()
        assert not isinstance(app.screen, ArchiveCreationScreen)


@pytest.mark.asyncio
async def test_zip_button_modal(tmp_path: Path) -> None:
    from rovr.screens import ArchiveCreationScreen

    open(tmp_path / "test_file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(ZipButton)
        await iter_until(pilot, lambda: isinstance(app.screen, ArchiveCreationScreen))
        await pilot.press("escape")
        await iter_until(
            pilot, lambda: not isinstance(app.screen, ArchiveCreationScreen)
        )


@pytest.mark.asyncio
async def test_zip_button_creates_archive(tmp_path: Path) -> None:
    from rovr.screens import ArchiveCreationScreen

    open(tmp_path / "test_file.txt", "w").close()
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(ZipButton)
        await iter_until(pilot, lambda: isinstance(app.screen, ArchiveCreationScreen))
        assert isinstance(app.screen, ArchiveCreationScreen)
        await pilot.press("enter")
        await iter_until(
            pilot, lambda: not isinstance(app.screen, ArchiveCreationScreen)
        )
        assert not isinstance(app.screen, ArchiveCreationScreen)
        assert any(f.endswith(".zip") for f in os.listdir(tmp_path))


@pytest.mark.asyncio
async def test_unzip_button(tmp_path: Path) -> None:
    from rovr.screens import ModalInput

    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(UnzipButton)
        await pilot.pause()
        assert not isinstance(app.screen, ModalInput)


@pytest.mark.asyncio
async def test_unzip_button_modal(tmp_path: Path) -> None:
    import zipfile

    from rovr.screens import ModalInput

    zip_path = tmp_path / "test_archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "hello")
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(UnzipButton)
        await iter_until(pilot, lambda: isinstance(app.screen, ModalInput))
        assert isinstance(app.screen, ModalInput)
        await pilot.press("escape")
        await iter_until(pilot, lambda: not isinstance(app.screen, ModalInput))
        assert not isinstance(app.screen, ModalInput)


@pytest.mark.asyncio
async def test_unzip_button_extracts_archive(tmp_path: Path) -> None:
    import zipfile

    from rovr.screens import ModalInput

    zip_path = tmp_path / "test_archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "hello")
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(UnzipButton)
        await iter_until(pilot, lambda: isinstance(app.screen, ModalInput))
        assert isinstance(app.screen, ModalInput)
        await pilot.press("enter")
        await iter_until(pilot, lambda: not isinstance(app.screen, ModalInput))
        assert not isinstance(app.screen, ModalInput)
        assert os.path.isdir(tmp_path / "test_archive")


@pytest.mark.asyncio
async def test_switch_to_extension(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(SortOrderButton)
        await iter_until(pilot, lambda: app.query_one(SortOrderPopup).display)
        assert (popup := app.query_one(SortOrderPopup)).display
        popup.action_cursor_down()
        await pilot.pause()
        popup.action_select()
        await iter_until(
            pilot, lambda: app.query_one(StateManager).sort_by == "extension"
        )


@pytest.mark.asyncio
async def test_sort_actions_accept_direction(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)):
        button = app.query_one(SortOrderButton)
        state_manager = app.query_one(StateManager)

        button.action_extension(True)
        assert state_manager.get_sort_prefs() == ("extension", True)

        button.action_name()
        assert state_manager.get_sort_prefs() == ("name", True)

        button.action_size(False)
        assert state_manager.get_sort_prefs() == ("size", False)


@pytest.mark.asyncio
async def test_toggles(tmp_path: Path) -> None:
    app = Application(tmp_path.as_posix())
    open(tmp_path / "test_file.txt", "w").close()
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        await pilot.click(SortOrderButton)
        await iter_until(pilot, lambda: app.query_one(SortOrderPopup).display)
        assert (popup := app.query_one(SortOrderPopup)).display
        popup.highlighted = popup.get_option_index("descending")
        await pilot.pause()
        popup.action_select()
        await iter_until(pilot, lambda: app.query_one(StateManager).sort_descending)
