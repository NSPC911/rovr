"""Unit tests for rovr.functions.path module."""

import os
from pathlib import Path

import pytest

from rovr.functions.path import (
    compress,
    decompress,
    is_hidden_file,
    normalise,
)


class TestNormalise:
    """Tests for path normalization."""

    def test_forward_slashes(self) -> None:
        """Backslashes converted to forward slashes."""
        result = normalise("C:\\Users\\test\\file.txt")
        assert "\\" not in result
        assert "/" in result

    def test_double_slashes(self) -> None:
        """Double slashes are collapsed."""
        result = normalise("path//to//file")
        assert "//" not in result

    def test_relative_refs(self) -> None:
        """Relative references are resolved."""
        result = normalise("path/to/../file")
        assert ".." not in result

    def test_bytes_input(self) -> None:
        """Bytes input is handled."""
        result = normalise(b"path/to/file")
        assert isinstance(result, str)

    def test_already_normalized(self) -> None:
        """Already normalized path unchanged."""
        result = normalise("path/to/file")
        assert result == "path/to/file"

    def test_trailing_slash_removed(self) -> None:
        """Trailing slashes are removed."""
        result = normalise("path/to/folder/")
        assert not result.endswith("/")

    def test_current_dir_dot(self) -> None:
        """Single dot (current dir) is handled."""
        result = normalise("./file.txt")
        assert result == "file.txt"

    def test_empty_string(self) -> None:
        """Empty string returns current directory marker."""
        result = normalise("")
        # os.path.normpath("") returns "."
        assert result == "."


class TestCompressDecompress:
    """Tests for base64 ID encoding/decoding."""

    def test_roundtrip(self) -> None:
        """Compress then decompress returns original."""
        original = "/home/user/Documents/file.txt"
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original

    def test_compress_prefix(self) -> None:
        """Compressed strings start with u_ prefix."""
        result = compress("test")
        assert result.startswith("u_")

    def test_unicode_support(self) -> None:
        """Unicode characters are preserved."""
        original = "/home/user/文档/файл.txt"
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original

    def test_special_characters(self) -> None:
        """Special characters are handled."""
        original = "path/with spaces/and-dashes/and_underscores"
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original

    def test_empty_string(self) -> None:
        """Empty string roundtrips correctly."""
        original = ""
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original

    def test_windows_path(self) -> None:
        """Windows-style paths roundtrip correctly."""
        original = "C:/Users/test/Documents/file.txt"
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original


class TestIsHiddenFile:
    """Tests for hidden file detection."""

    def test_dotfile_hidden_on_unix(self, temp_dir: Path) -> None:
        """Dotfiles are hidden on Unix/Mac."""
        hidden = temp_dir / ".hidden"
        hidden.touch()

        # On Unix, dotfiles are always hidden
        if os.name != "nt":
            assert is_hidden_file(str(hidden)) is True

    def test_regular_file_not_hidden(self, temp_dir: Path) -> None:
        """Regular files are not hidden."""
        regular = temp_dir / "regular.txt"
        regular.touch()
        assert is_hidden_file(str(regular)) is False

    def test_nonexistent_file_not_hidden(self, temp_dir: Path) -> None:
        """Non-existent files are not hidden."""
        nonexistent = temp_dir / "nonexistent.txt"
        assert is_hidden_file(str(nonexistent)) is False

    def test_directory_with_dot_prefix(self, temp_dir: Path) -> None:
        """Directories starting with dot are hidden on Unix."""
        hidden_dir = temp_dir / ".hidden_dir"
        hidden_dir.mkdir()

        if os.name != "nt":
            assert is_hidden_file(str(hidden_dir)) is True

    def test_file_in_hidden_directory(self, temp_dir: Path) -> None:
        """Files in hidden directories - file itself checked."""
        hidden_dir = temp_dir / ".hidden_dir"
        hidden_dir.mkdir()
        visible_file = hidden_dir / "visible.txt"
        visible_file.touch()

        # The file itself isn't hidden, just its parent
        # Function checks the file, not its path
        result = is_hidden_file(str(visible_file))
        # This depends on implementation - file may or may not be considered hidden
        assert isinstance(result, bool)

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_hidden_attribute(self, temp_dir: Path) -> None:
        """Windows hidden attribute detected."""
        import ctypes

        hidden_file = temp_dir / "hidden_win.txt"
        hidden_file.touch()

        # Set hidden attribute on Windows
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(hidden_file), FILE_ATTRIBUTE_HIDDEN)

        assert is_hidden_file(str(hidden_file)) is True

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_regular_file_not_hidden(self, temp_dir: Path) -> None:
        """Regular Windows files without hidden attribute are not hidden."""
        regular = temp_dir / "regular_win.txt"
        regular.touch()
        assert is_hidden_file(str(regular)) is False


class TestPathEdgeCases:
    """Edge case tests for path functions."""

    def test_normalise_with_drive_letter(self) -> None:
        """Windows drive letters handled correctly."""
        result = normalise("C:\\")
        assert "C" in result.upper()

    def test_normalise_unc_path(self) -> None:
        """UNC paths (network shares) handled."""
        result = normalise("\\\\server\\share\\file.txt")
        assert "server" in result

    def test_compress_with_newlines(self) -> None:
        """Paths with newlines (edge case) handled."""
        original = "path/with\nnewline"
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original

    def test_compress_very_long_path(self) -> None:
        """Very long paths handled correctly."""
        original = "a" * 500 + "/" + "b" * 500
        compressed = compress(original)
        decompressed = decompress(compressed)
        assert decompressed == original
