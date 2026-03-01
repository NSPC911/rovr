import os
from pathlib import Path

import pytest

from rovr.functions import path as path_utils


def test_normalise() -> None:
    the_path = os.getcwd()
    assert path_utils.normalise(the_path) == Path(the_path).as_posix()
    with pytest.raises(ValueError):
        path_utils.normalise()


def test_compress_decompress() -> None:
    from textual.widgets import Static

    the_path = os.getcwd()
    compressed = path_utils.compress(the_path)
    assert Static(id=compressed, classes=compressed)
    decompressed = path_utils.decompress(compressed)
    assert decompressed == the_path


def test_extension_sort_key() -> None:
    files = [
        {"name": "file.txt"},
        {"name": "archive.zip"},
        {"name": "README"},
        {"name": ".env"},
        {"name": "script.py"},
    ]
    sorted_files = sorted(files, key=path_utils.get_extension_sort_key)
    expected_order = [
        {"name": "README"},
        {"name": ".env"},
        {"name": "script.py"},
        {"name": "file.txt"},
        {"name": "archive.zip"},
    ]
    assert sorted_files == expected_order


def test_filtered_dir_names(tmp_path: Path) -> None:
    import string
    from random import choices

    for _ in range(10):
        random_name = "".join(choices(string.ascii_letters + string.digits, k=8))
        open(tmp_path / random_name, "w").close()

    dir_names = set(f.name for f in tmp_path.iterdir())
    filtered = path_utils.get_filtered_dir_names(tmp_path.as_posix())
    assert filtered == dir_names


def test_file_type(tmp_path: Path) -> None:
    import sys

    # file
    open(tmp_path / "file.txt", "w").close()
    assert path_utils.file_is_type(tmp_path.joinpath("file.txt").as_posix()) == "file"

    # directory
    os.makedirs(tmp_path / "folder")
    assert (
        path_utils.file_is_type(tmp_path.joinpath("folder").as_posix()) == "directory"
    )

    # symlink
    try:
        os.symlink(tmp_path / "file.txt", tmp_path / "link")
        assert (
            path_utils.file_is_type(tmp_path.joinpath("link").as_posix()) == "symlink"
        )
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation failed, skipping test")

    # junction (if windows)
    if sys.platform == "win32":
        # use the folder from before
        import subprocess

        output = subprocess.run(
            [
                "mklink",
                "/J",
                str(tmp_path / "junction"),
                str(tmp_path / "folder"),
            ],
            shell=True,
            capture_output=True,
            text=True,
        )
        if output.returncode != 0:
            pytest.skip("Junction creation failed, skipping test")
        else:
            assert (
                path_utils.file_is_type(tmp_path.joinpath("junction").as_posix())
                == "junction"
            )


def test_ensure_existing_directory(tmp_path: Path) -> None:
    # basically check the directory it goes to if the target directory doesnt exist or isnt a directory
    target_dir = tmp_path / "nonexistent" / "subdir" / "target" / "dir"
    ensured = path_utils.ensure_existing_directory(target_dir.as_posix())
    assert ensured == tmp_path.as_posix()


def test_get_recursive_files(tmp_path: Path) -> None:
    import string
    from random import choices

    path1 = tmp_path / "path1"
    path2 = tmp_path / "path2"
    path1.mkdir()
    path2.mkdir()
    for _ in range(5):
        random_name = "".join(choices(string.ascii_letters + string.digits, k=8))
        open(path1 / random_name, "w").close()

    for _ in range(10):
        random_name = "".join(choices(string.ascii_letters + string.digits, k=8))
        open(path2 / random_name, "w").close()
    files = path_utils.get_recursive_files(tmp_path.as_posix())
    assert len(files) == 15
    files, folders = path_utils.get_recursive_files(
        tmp_path.as_posix(), with_folders=True
    )
    assert len(folders) == 2 and len(files) == 15
