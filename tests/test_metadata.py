import os
from pathlib import Path

from rovr.footer import MetadataContainer


def test_info_of_dir_entry(tmp_path: Path) -> None:
    """Test the info_of_dir_entry function with various file types and permissions."""
    os.chdir(tmp_path)
    metadata = MetadataContainer()

    # Create test files with different permissions
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")

    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    dir_entry: os.DirEntry = next(os.scandir(tmp_path))
    # dir_entry.path = str(test_file)

    result = metadata.info_of_dir_entry(dir_entry, "File")
    assert result.startswith("-")
    assert len(result) == 10

    dir_entry.path = str(test_dir)
    result = metadata.info_of_dir_entry(dir_entry, "Directory")
    assert result.startswith("d")
    assert len(result) == 10

    test_symlink = tmp_path / "test_symlink"
    test_symlink.symlink_to(test_file)
    dir_entry.path = str(test_symlink)
    result = metadata.info_of_dir_entry(dir_entry, "Symlink")
    assert result.startswith("l")
    assert len(result) == 10

    result = metadata.info_of_dir_entry(dir_entry, "Unknown")
    assert result == "???????"

    result = metadata.info_of_dir_entry(dir_entry, "Junction")
    assert result.startswith("j")
    assert len(result) == 10

    dir_entry.path = str(tmp_path / "non_existent_file.txt")
    result = metadata.info_of_dir_entry(dir_entry, "File")
    assert result == "?????????"

    dir_entry.path = str(test_file)
    result = metadata.info_of_dir_entry(dir_entry, "File")
    assert result.startswith("-")
    assert len(result) == 10
    valid_chars = set("-rwx")
    assert all(c in valid_chars for c in result[1:])
