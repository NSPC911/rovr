from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any, cast

import pytest
from textual.content import Content
from textual.worker import Worker

from rovr.app import Application
from rovr.classes.textual_options import ClipboardSelection, FileListSelectionWidget
from rovr.footer.clipboard_container import Clipboard
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


@pytest.mark.asyncio
async def test_checked_component_style_preserves_file_style(tmp_path: Path) -> None:
    file_path = tmp_path / "checked.txt"
    file_path.touch()

    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        worker = cast(Worker, app.file_list.update_file_list(add_to_session=False))
        await worker.wait()
        await app.file_list.toggle_mode()

        option = next(
            option for option in app.file_list.options if option.label == file_path.name
        )
        app.file_list.select(option)

        classes = app.file_list._get_option_component_classes(option)
        assert classes[0] == "selection-list--option-checked"
        assert (
            "background"
            not in app.file_list.get_component_styles(
                "selection-list--option-checked"
            ).get_rules()
        )
        assert "selection-list--option-checked" in Clipboard.COMPONENT_CLASSES

        combined_style = app.file_list.get_visual_style(
            "option-list--option", *classes, "filelist--cut--highlighted"
        )
        checked_style = app.file_list.get_visual_style(
            "option-list--option", "selection-list--option-checked"
        )
        file_style = app.file_list.get_visual_style(
            "option-list--option", "filelist--cut--highlighted"
        )
        assert combined_style.foreground == checked_style.foreground
        assert combined_style.background == file_style.background


@pytest.mark.asyncio
async def test_checked_clipboard_option_renders(tmp_path: Path) -> None:
    file_path = tmp_path / "checked.txt"
    file_path.touch()

    app = Application(tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        option = ClipboardSelection(
            prompt=Content(str(file_path)),
            text=str(file_path),
            type_of_selection="copy",
        )
        app.Clipboard.insert_selection_at_beginning(option)
        app.Clipboard.select(option)
        await pilot.pause()

        assert app.Clipboard._get_option_component_classes(option) == [
            "selection-list--option-checked"
        ]
        assert app.Clipboard.render_line(0).text.strip()
