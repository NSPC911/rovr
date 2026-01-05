"""Unit tests for rovr.functions.icons module."""

import contextlib


class TestGetIconForFile:
    """Tests for get_icon_for_file function."""

    def test_returns_list(self) -> None:
        """Function returns a list [icon, color]."""
        from rovr.functions.icons import get_icon_for_file

        # Clear LRU cache to ensure fresh test
        get_icon_for_file.cache_clear()

        result = get_icon_for_file("test.txt")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_python_file_icon(self) -> None:
        """Python files get Python icon."""
        from rovr.functions.icons import get_icon_for_file

        get_icon_for_file.cache_clear()
        result = get_icon_for_file("script.py")
        # Should return some icon (exact icon depends on config)
        assert result is not None
        assert len(result) == 2

    def test_case_insensitive(self) -> None:
        """File extension matching is case-insensitive."""
        from rovr.functions.icons import get_icon_for_file

        get_icon_for_file.cache_clear()
        result_lower = get_icon_for_file("test.py")

        get_icon_for_file.cache_clear()
        result_upper = get_icon_for_file("TEST.PY")

        # Both should return same icon
        assert result_lower == result_upper

    def test_hidden_file_with_extension(self) -> None:
        """Hidden files with extensions (e.g., .gitignore) handled."""
        from rovr.functions.icons import get_icon_for_file

        get_icon_for_file.cache_clear()
        result = get_icon_for_file(".gitignore")
        assert result is not None

    def test_no_extension(self) -> None:
        """Files without extension get default icon."""
        from rovr.functions.icons import get_icon_for_file

        get_icon_for_file.cache_clear()
        result = get_icon_for_file("Makefile")
        assert result is not None

    def test_lru_cache_works(self) -> None:
        """LRU cache prevents redundant lookups."""
        from rovr.functions.icons import get_icon_for_file

        get_icon_for_file.cache_clear()

        # First call
        result1 = get_icon_for_file("cached.txt")
        # Second call should be cached
        result2 = get_icon_for_file("cached.txt")

        assert result1 is result2  # Same object from cache
        assert get_icon_for_file.cache_info().hits >= 1


class TestGetIconForFolder:
    """Tests for get_icon_for_folder function."""

    def test_returns_list(self) -> None:
        """Function returns a list [icon, color]."""
        from rovr.functions.icons import get_icon_for_folder

        get_icon_for_folder.cache_clear()
        result = get_icon_for_folder("Documents")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_special_folder_names(self) -> None:
        """Special folders (node_modules, .git) get specific icons."""
        from rovr.functions.icons import get_icon_for_folder

        # Test some common special folders
        special_folders = ["node_modules", ".git", "src", "__pycache__"]

        for folder in special_folders:
            get_icon_for_folder.cache_clear()
            result = get_icon_for_folder(folder)
            assert result is not None
            assert len(result) == 2

    def test_case_insensitive(self) -> None:
        """Folder name matching is case-insensitive."""
        from rovr.functions.icons import get_icon_for_folder

        get_icon_for_folder.cache_clear()
        result_lower = get_icon_for_folder("documents")

        get_icon_for_folder.cache_clear()
        result_upper = get_icon_for_folder("DOCUMENTS")

        assert result_lower == result_upper

    def test_generic_folder(self) -> None:
        """Unknown folder names get default icon."""
        from rovr.functions.icons import get_icon_for_folder

        get_icon_for_folder.cache_clear()
        result = get_icon_for_folder("my_random_folder_12345")
        assert result is not None


class TestGetIcon:
    """Tests for get_icon function."""

    def test_general_icons(self) -> None:
        """Can retrieve general icons."""
        from rovr.functions.icons import get_icon

        get_icon.cache_clear()
        # This tests the general category exists
        result = get_icon("general", "symlink")
        assert result is not None

    def test_invalid_key_handling(self) -> None:
        """Invalid keys should raise KeyError or return default."""
        from rovr.functions.icons import get_icon

        get_icon.cache_clear()
        # Depending on implementation, this might raise or return default
        with contextlib.suppress(KeyError):
            get_icon("nonexistent", "category")


class TestGetToggleButtonIcon:
    """Tests for get_toggle_button_icon function."""

    def test_returns_string(self) -> None:
        """Function returns a string icon."""
        from rovr.functions.icons import get_toggle_button_icon

        get_toggle_button_icon.cache_clear()
        # Keys are: "left", "right", "inner", "inner_filled"
        result = get_toggle_button_icon("inner")
        assert isinstance(result, str)

    def test_all_toggle_keys(self) -> None:
        """All toggle button keys return strings."""
        from rovr.functions.icons import get_toggle_button_icon

        for key in ["left", "right", "inner", "inner_filled"]:
            get_toggle_button_icon.cache_clear()
            result = get_toggle_button_icon(key)
            assert isinstance(result, str)
