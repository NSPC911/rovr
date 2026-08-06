import sys

import pytest

from rovr.navigation_widgets.path_input import should_exclude_hidden


def test_should_exclude_hidden_empty() -> None:
    assert not should_exclude_hidden("")


def test_should_exclude_hidden_dot_terminal() -> None:
    """User typed '.' alone or as last component → show dotfiles."""
    assert not should_exclude_hidden(".")
    assert not should_exclude_hidden("/home/.")


def test_should_exclude_hidden_double_dot_filters() -> None:
    """.. represents navigation, so it MUST filter."""
    assert should_exclude_hidden("..")
    assert should_exclude_hidden("/home/..")
    assert should_exclude_hidden("C:\\Windows\\..")


def test_should_exclude_hidden_dotfile_no_filter() -> None:
    assert not should_exclude_hidden("/foo/.config")
    assert should_exclude_hidden("/foo/.hidden_dir/")
    assert not should_exclude_hidden("/home/...cache")


def test_should_exclude_hidden_visible_filters() -> None:
    assert should_exclude_hidden("/home")
    assert should_exclude_hidden("/home/")
    assert should_exclude_hidden("/home/projects")
    assert should_exclude_hidden("C:/Users/Me/Documents")


@pytest.mark.skipif(sys.platform != "win32", reason="Need to be on Windows")
def test_should_exclude_hidden_backslash_separator() -> None:
    """Backslashes should work as separators too."""
    assert not should_exclude_hidden("C:\\foo\\.git")


def test_should_exclude_hidden_trailing_slashes_no_separator() -> None:
    """Path with trailing slashes but no final component still filters
    (same behaviour as the original implementation)."""
    assert should_exclude_hidden("/home/foo///")
