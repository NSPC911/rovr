import os
import sys
from pathlib import Path

import pytest

from .conftest import iter_until


@pytest.mark.asyncio
async def test_default_pinned_sidebar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_map = {
        "Documents": tmp_path / "Documents",
        "Downloads": tmp_path / "Downloads",
        "Music": tmp_path / "Music",
        "Pictures": tmp_path / "Pictures",
        "Desktop": tmp_path / "Desktop",
        "Home": tmp_path,
        "Videos": tmp_path / "Videos",
    }
    # change variables to platformdirs
    if sys.platform == "win32":
        for name, path in base_map.items():
            path.mkdir(exist_ok=True)
            monkeypatch.setenv(f"{name.upper()}_DIR", str(path))
    elif sys.platform == "darwin":
        xdg_map = {
            "Documents": "XDG_DOCUMENTS_DIR",
            "Downloads": "XDG_DOWNLOAD_DIR",
            "Music": "XDG_MUSIC_DIR",
            "Pictures": "XDG_PICTURES_DIR",
            "Desktop": "XDG_DESKTOP_DIR",
            "Videos": "XDG_VIDEOS_DIR",
        }
        for name, path in base_map.items():
            path.mkdir(exist_ok=True)
            if name == "Home":
                monkeypatch.setenv("HOME", str(path))
            else:
                monkeypatch.setenv(xdg_map[name], str(path))
    else:
        xdg_map = {
            "Documents": "XDG_DOCUMENTS_DIR",
            "Downloads": "XDG_DOWNLOAD_DIR",
            "Music": "XDG_MUSIC_DIR",
            "Pictures": "XDG_PICTURES_DIR",
            "Desktop": "XDG_DESKTOP_DIR",
            "Videos": "XDG_VIDEOS_DIR",
        }
        for name, path in base_map.items():
            path.mkdir(exist_ok=True)
            if name == "Home":
                monkeypatch.setenv("HOME", str(path))
            else:
                monkeypatch.setenv(xdg_map[name], str(path))

    from rovr.app import Application

    app = Application(tmp_path.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        sidebar = app.query_one("PinnedSidebar")
        await iter_until(pilot, lambda: bool(app.file_list.options))
        for option in sidebar.list_of_options:
            if hasattr(option, "label"):
                assert option.label in base_map
                base_map.pop(option.label)
            elif option.prompt.strip() == "Pinned":
                break
        assert not base_map


@pytest.mark.asyncio
async def test_add_pins(tmp_path: Path) -> None:
    from textual.worker import Worker

    from rovr.app import Application
    from rovr.core import PinnedSidebar
    from rovr.functions import pins

    app = Application(tmp_path.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        sidebar = app.query_one(PinnedSidebar)
        test = tmp_path / "TestFolder"
        test.mkdir()
        pins.add_pin("TestFolder", test.as_posix())
        worker: Worker = sidebar.reload_pins()
        await worker.wait()
        await pilot.pause()
        found: bool = False
        found_at: int | None = None
        for index, option in enumerate(sidebar.list_of_options):
            if getattr(option, "label", "") == "TestFolder":
                found = True
                found_at = index
                break
        assert found and found_at is not None

        # now check whether you can cd
        sidebar.highlighted = found_at
        sidebar.action_select()
        await iter_until(pilot, lambda: Path(os.getcwd()).as_posix() == test.as_posix())


@pytest.mark.asyncio
async def test_pin_no_exist(tmp_path: Path) -> None:
    from rovr.app import Application
    from rovr.functions import pins

    app = Application(tmp_path.as_posix())

    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        test = tmp_path / "TestFolder"
        with pytest.raises(FileNotFoundError):
            pins.add_pin("TestFolder", test.as_posix())
        open(tmp_path / "TestFile.txt", "w").close()
        with pytest.raises(ValueError):
            pins.add_pin("TestFile", (tmp_path / "TestFile.txt").as_posix())
