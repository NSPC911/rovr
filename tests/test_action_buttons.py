import asyncio
import os
from tempfile import TemporaryDirectory

import pytest
from rich.console import Console  # noqa: F401
from textual.widgets import SelectionList

from rovr.action_buttons import (
    CopyButton,
    CutButton,
    DeleteButton,
    NewItemButton,  # noqa: F401
    PasteButton,
    RenameItemButton,  # noqa: F401
    UnzipButton,  # noqa: F401
    ZipButton,  # noqa: F401
)
from rovr.app import Application

# conout = open("CONOUT$", "w")  # noqa: SIM115
# console = Console(file=conout)


@pytest.mark.asyncio
async def test_copy_button() -> None:
    app = Application()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )


@pytest.mark.asyncio
async def test_cut_button() -> None:
    app = Application()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_copy_to_cut() -> None:
    app = Application()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_cut_to_copy() -> None:
    app = Application()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click(CutButton)
        await pilot.pause()
        await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )


@pytest.mark.asyncio
async def test_double_copy() -> None:
    app = Application()
    async with app.run_test() as pilot:
        for _ in range(2):
            await pilot.pause()
            await pilot.click(CopyButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "copy"
        )


@pytest.mark.asyncio
async def test_double_cut() -> None:
    app = Application()
    async with app.run_test() as pilot:
        for _ in range(2):
            await pilot.pause()
            await pilot.click(CutButton)
        await pilot.pause()
        assert len(app.query_one("Clipboard", SelectionList).options) == 1
        assert (
            app.query_one("Clipboard", SelectionList)
            .get_option_at_index(0)
            .value.type_of_selection
            == "cut"
        )


@pytest.mark.asyncio
async def test_paste_button() -> None:
    with TemporaryDirectory() as temp_dir:
        app = Application(startup_path=temp_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click(CopyButton)
            await pilot.pause()
            await pilot.click(PasteButton)
            await asyncio.sleep(1)
            # console.print(app.screen.tree)
            assert False
            # TODO: also query the file list in the paste screen on what is being pasted


@pytest.mark.asyncio
async def test_delete_button() -> None:
    with (
        TemporaryDirectory() as temp_dir,
        open(os.path.join(temp_dir, "test_file.txt"), "w") as _,  # noqa: F841
    ):
        app = Application(startup_path=temp_dir)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert (
                app.file_list.get_option_at_index(0).dir_entry.name == "test_file.txt"
            )
            app.file_list.highlighted_option = app.file_list.get_option_at_index(
                0
            )  # ty: ignore
            await pilot.click(DeleteButton)
            await pilot.pause()
            # console.print(app.screen.tree)
            assert False
