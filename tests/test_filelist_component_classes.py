from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any, cast

import pytest
from textual.worker import Worker

from rovr.app import Application
from rovr.classes.textual_options import FileListSelectionWidget
from rovr.variables.constants import config, os_type


def _set_hidden_attribute(file_path: Path) -> bool:
    if os_type != "Windows":
        return True
    try:
        SetFileAttributesW = ctypes.windll.kernel32.SetFileAttributesW
        SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        SetFileAttributesW.restype = ctypes.c_int
        return bool(SetFileAttributesW(str(file_path), 0x02))
    except (OSError, AttributeError):
        return False


@pytest.mark.asyncio
async def test_hidden_file_adds_component_class(tmp_path: Path) -> None:
    if os_type == "Windows":
        hidden_file = tmp_path / "hidden.txt"
        hidden_file.touch()
        if not _set_hidden_attribute(hidden_file):
            pytest.skip("Unable to mark file as hidden")
    else:
        hidden_file = tmp_path / ".hidden.txt"
        hidden_file.touch()

    interface_config = cast(dict[str, Any], config).get("interface", {})
    original_show_hidden = interface_config.get("show_hidden_files")
    interface_config["show_hidden_files"] = True
    try:
        app = Application(tmp_path.as_posix())
        async with app.run_test(size=(143, 37)) as pilot:
            await pilot.pause()
            worker = cast(Worker, app.file_list.update_file_list(add_to_session=False))
            await worker.wait()
            await pilot.pause()

            option = next(
                option
                for option in app.file_list.options
                if isinstance(option, FileListSelectionWidget)
                and option.label == hidden_file.name
            )
            classes = option.get_component_classes()
            assert "filelist--hidden" in classes
    finally:
        interface_config["show_hidden_files"] = original_show_hidden


@pytest.mark.asyncio
async def test_working_symlink_adds_component_class(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.touch()
    link_path = tmp_path / "target-link.txt"
    try:
        link_path.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink not supported: {exc}")

    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        worker = cast(Worker, app.file_list.update_file_list(add_to_session=False))
        await worker.wait()
        await pilot.pause()

        option = next(
            option
            for option in app.file_list.options
            if isinstance(option, FileListSelectionWidget)
            and option.label == link_path.name
        )
        classes = option.get_component_classes()
        assert "filelist--link" in classes
