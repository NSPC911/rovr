import os
from pathlib import Path

import pytest

from rovr.classes.textual_validators import (
    IsValidFilePath,
    PathNoLongerExists,
)


def test_is_valid_file_path() -> None:
    validator = IsValidFilePath()
    assert validator.validate("valid_filename.txt").is_valid
    assert not validator.validate("invalid\u0000filename.txt").is_valid


def test_path_no_longer_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validator = PathNoLongerExists()
    existing_file = tmp_path / "existing_file.txt"
    existing_file.touch()
    assert not validator.validate("existing_file.txt").is_valid
    if os.name == "nt":
        assert not validator.validate("EXISTING_FILE.txt").is_valid
    assert validator.validate("non_existent_file.txt").is_valid


def test_is_valid_file_path_absolute_paths() -> None:
    """Test IsValidFilePath validator with absolute paths."""
    validator = IsValidFilePath()

    # Test valid absolute paths on different platforms
    if os.name == "nt":  # Windows
        assert validator.validate("C:\\Users\\test\\valid_file.txt").is_valid
        assert validator.validate("C:/Users/test/valid_file.txt").is_valid
    else:  # Unix-like
        assert validator.validate("/tmp/valid_file.txt").is_valid
        assert validator.validate("/home/user/valid_file.txt").is_valid

    # Test invalid absolute paths
    if os.name == "nt":
        assert not validator.validate("C:\\Users\\test\\invalid" + chr(0) + "file.txt").is_valid
    else:
        assert not validator.validate("/tmp/invalid" + chr(0) + "file.txt").is_valid


def test_path_no_longer_exists_absolute_paths(tmp_path: Path) -> None:
    """Test PathNoLongerExists validator with absolute paths."""
    validator = PathNoLongerExists()

    # Create a test file with absolute path
    test_file = tmp_path / "test_file.txt"
    test_file.touch()

    # Test with absolute path - should fail (file exists)
    assert not validator.validate(str(test_file)).is_valid

    # Test with non-existent absolute path - should pass
    non_existent = tmp_path / "non_existent.txt"
    assert validator.validate(str(non_existent)).is_valid

    # Test with absolute directory path
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    assert not validator.validate(str(test_dir)).is_valid


def test_mixed_relative_and_absolute_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test both validators handle mixed relative and absolute paths correctly."""
    monkeypatch.chdir(tmp_path)

    # Create test files
    existing_file = tmp_path / "existing.txt"
    existing_file.touch()

    # Test IsValidFilePath
    path_validator = IsValidFilePath()
    assert path_validator.validate("relative_valid.txt").is_valid  # relative
    assert path_validator.validate(str(existing_file)).is_valid  # absolute

    # Test PathNoLongerExists
    exists_validator = PathNoLongerExists()
    assert not exists_validator.validate("existing.txt").is_valid  # relative, exists
    assert not exists_validator.validate(str(existing_file)).is_valid  # absolute, exists
    assert exists_validator.validate("non_existent.txt").is_valid  # relative, doesn't exist
    assert exists_validator.validate(str(tmp_path / "non_existent.txt")).is_valid  # absolute, doesn't exist
