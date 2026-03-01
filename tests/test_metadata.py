import logging
import os
import sys
from pathlib import Path

from rovr.footer import MetadataContainer


def test_info_of_dir_entry(tmp_path: Path) -> None:
    """Test the info_of_dir_entry function with various file types and permissions."""
    os.chdir(tmp_path)
    metadata = MetadataContainer()

    # Create test files with different permissions
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")
    dir_entry: os.DirEntry = next(os.scandir(tmp_path))

    result = metadata.info_of_dir_entry(dir_entry, "File")
    assert result.startswith("-")
    assert len(result) == 10

    os.remove(test_file)
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    dir_entry: os.DirEntry = next(os.scandir(tmp_path))

    result = metadata.info_of_dir_entry(dir_entry, "Directory")
    assert result.startswith("d")
    assert len(result) == 10

    os.rmdir(test_dir)
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")
    test_symlink = tmp_path / "test_symlink"
    test_symlink.symlink_to(test_file)
    for entry in os.scandir(tmp_path):
        if entry.name == "test_symlink":
            dir_entry = entry
            break

    result = metadata.info_of_dir_entry(dir_entry, "Symlink")
    assert result.startswith("l")
    assert len(result) == 10

    os.remove(test_symlink)
    os.remove(test_file)

    result = metadata.info_of_dir_entry(dir_entry, "Unknown")
    assert result == "?????????"

    result = metadata.info_of_dir_entry(dir_entry, "File")
    assert result == "?????????"

    # junction (if windows)
    if sys.platform == "win32":
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
            # assume pass, cant really bother if it doesn't work
            logging.warning(
                "Failed to create junction, skipping test: %s", output.stderr
            )
        dir_entry = next(os.scandir(tmp_path))
        result = metadata.info_of_dir_entry(dir_entry, "Junction")
        assert result.startswith("j")
        assert len(result) == 10
