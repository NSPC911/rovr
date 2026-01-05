"""Shared pytest fixtures for rovr tests."""

import tarfile
import tempfile
import zipfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide an isolated temporary directory for file operations.

    Yields:
        Path to temporary directory.
    """
    # Use ignore_cleanup_errors for Windows file locking issues
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        yield Path(td)


@pytest.fixture
def sample_file_structure(temp_dir: Path) -> Path:
    """Create a realistic test file structure.

    Structure:
        temp_dir/
        ├── folder1/
        │   └── nested.txt
        ├── folder2/
        ├── file1.txt
        ├── file2.py
        ├── image.png (empty)
        └── .hidden

    Returns:
        Path to the temp directory with file structure.
    """
    # Directories
    (temp_dir / "folder1").mkdir()
    (temp_dir / "folder2").mkdir()
    (temp_dir / "folder1" / "nested.txt").write_text("nested content")

    # Files
    (temp_dir / "file1.txt").write_text("hello world")
    (temp_dir / "file2.py").write_text("print('hello')")
    (temp_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header
    (temp_dir / ".hidden").touch()

    return temp_dir


@pytest.fixture
def app() -> Any:
    """Create a fresh Application instance for testing.

    Note: For most tests, use `async with app.run_test() as pilot:` pattern.

    Returns:
        Application instance.
    """
    from rovr.app import Application
    return Application()


@pytest.fixture
def sample_archive_structure(temp_dir: Path) -> dict[str, Path]:
    """Create various archive types for testing.

    Returns:
        Dict with archive paths:
            - zip: Simple ZIP archive
            - tar_gz: Tar.gz archive
            - nested_zip: ZIP with nested folders
            - empty_zip: Empty ZIP archive
    """
    archives = {}

    # Simple ZIP
    zip_path = temp_dir / "simple.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("readme.txt", "Hello!")
        zf.writestr("data.json", '{"key": "value"}')
    archives["zip"] = zip_path

    # Tar.gz
    tar_path = temp_dir / "archive.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        temp_file = temp_dir / "_temp.txt"
        temp_file.write_text("Tar content")
        tf.add(temp_file, arcname="content.txt")
        temp_file.unlink()
    archives["tar_gz"] = tar_path

    # Nested ZIP
    nested_zip_path = temp_dir / "nested.zip"
    with zipfile.ZipFile(nested_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("root.txt", "Root level")
        zf.writestr("level1/file.txt", "Level 1")
        zf.writestr("level1/level2/file.txt", "Level 2")
        zf.writestr("level1/level2/level3/file.txt", "Level 3")
    archives["nested_zip"] = nested_zip_path

    # Empty ZIP
    empty_zip_path = temp_dir / "empty.zip"
    with zipfile.ZipFile(empty_zip_path, "w") as zf:
        pass
    archives["empty_zip"] = empty_zip_path

    return archives


@pytest.fixture
def app_with_files(sample_file_structure: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Create Application instance with test files in CWD.

    Use this for integration tests that need files present.

    Returns:
        Application instance with files in CWD.
    """
    monkeypatch.chdir(sample_file_structure)
    from rovr.app import Application
    return Application()


@pytest.fixture(autouse=True)
def disable_file_watcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the file watcher worker during tests.

    The watch_for_changes_and_update worker uses sleep(1) in an infinite loop,
    which prevents clean test shutdown. This fixture patches it to be a no-op.
    """
    def noop_watcher(self: Any) -> None:
        """No-op replacement for file watcher."""
        pass

    # Patch before any Application import
    monkeypatch.setattr(
        "rovr.app.Application.watch_for_changes_and_update",
        noop_watcher
    )
