import os
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_default_pinned_sidebar(tmp_path: Path) -> None:
    dirs = {
        "Documents": tmp_path / "Documents",
        "Downloads": tmp_path / "Downloads",
        "Music": tmp_path / "Music",
        "Pictures": tmp_path / "Pictures",
        "Desktop": tmp_path / "Desktop",
        "Home": tmp_path,
        "Videos": tmp_path / "Videos",
    }
    # change variables to platformdirs
    if os.name == "nt":
        for name, path in dirs.items():
            path.mkdir(exist_ok=True)
            os.environ[f"WIN_PD_OVERRIDE_{name.upper()}"] = str(path)

    from rovr.app import Application

    app = Application(tmp_path.as_posix())

    async with app.run_test() as pilot:
        sidebar = app.query_one("PinnedSidebar")
        await pilot.pause(1)
        for option in sidebar.list_of_options:
            if hasattr(option, "label"):
                assert option.label in dirs
                dirs.pop(option.label)
            elif option.prompt.strip() == "Pinned":
                break


@pytest.mark.asyncio
async def test_add_pins(tmp_path: Path) -> None:
    from textual.worker import Worker

    from rovr.app import Application
    from rovr.core import PinnedSidebar
    from rovr.functions import pins

    app = Application(tmp_path.as_posix())

    async with app.run_test() as pilot:
        sidebar = app.query_one(PinnedSidebar)
        await pilot.pause()
        test = tmp_path / "TestFolder"
        test.mkdir()
        pins.add_pin("TestFolder", test.as_posix())
        worker: Worker = sidebar.reload_pins()
        await worker.wait()
        await pilot.pause(1)
        found: bool = False
        found_at: int | None = None
        for index, option in enumerate(sidebar.list_of_options):
            if hasattr(option, "label") and option.label == "TestFolder":
                found = True
                found_at = index
                break
        assert found and found_at is not None

        # now check whether you can cd
        sidebar.highlighted = found_at
        sidebar.action_select()
        await pilot.pause(1)
        assert Path(os.getcwd()).as_posix() == test.as_posix()


@pytest.mark.asyncio
async def test_pin_no_exist(tmp_path: Path) -> None:
    from rovr.app import Application
    from rovr.functions import pins

    app = Application(tmp_path.as_posix())

    async with app.run_test() as pilot:
        await pilot.pause()
        test = tmp_path / "TestFolder"
        with pytest.raises(FileNotFoundError):
            pins.add_pin("TestFolder", test.as_posix())
        open(tmp_path / "TestFile.txt", "w").close()
        with pytest.raises(ValueError):
            pins.add_pin("TestFile", (tmp_path / "TestFile.txt").as_posix())
