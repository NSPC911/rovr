import sys
from pathlib import Path

import pytest

from rovr.functions import icons
from rovr.variables.maps import ICONS


def test_smart(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.touch()
    file_icon = icons.get_icon_for_file(test_file.as_posix())
    assert file_icon == ICONS["file"]["txt"]

    test_folder = tmp_path / "test_folder"
    test_folder.mkdir()
    folder_icon = icons.get_icon_for_folder(test_folder.as_posix())
    assert folder_icon == ICONS["folder"]["default"]

    try:
        symlink_path = tmp_path / "symlink_to_test_file"
        symlink_path.symlink_to(test_file)
        symlink_icon = icons.get_icon_for_file(symlink_path.as_posix())
        assert symlink_icon == ICONS["general"]["symlink"]
    except (OSError, NotImplementedError):
        if sys.platform != "win32":
            pytest.skip("Symlink creation failed, skipping test")

    # test junction icon (only on Windows)
    if sys.platform == "win32":
        import subprocess

        output = subprocess.run(
            [
                "mklink",
                "/J",
                # because windows cmd considers forward slashes as switches
                (tmp_path / "folder").as_posix().replace("/", "\\"),
                test_folder.as_posix().replace("/", "\\"),
            ],
            shell=True,
            capture_output=True,
            text=True,
        )
        if output.returncode != 0:
            # assume pass, can't really bother if it doesn't work
            pytest.skip("Junction creation failed, skipping test")
        else:
            junction_icon = icons.get_icon_for_folder((tmp_path / "folder").as_posix())
            assert junction_icon == ICONS["general"]["symlink"]
