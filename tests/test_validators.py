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
