import sys

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input
from textual_autocomplete import TargetState

from rovr.navigation_widgets.path_input import (
    PathAutoCompleteInput,
    should_exclude_hidden,
)


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


@pytest.mark.skipif(sys.platform != "win32", reason="Need to be on Windows")
def test_search_string_accepts_backslash_separator() -> None:
    autocomplete = PathAutoCompleteInput(Input())
    value = "C:/Users/example\\"

    assert autocomplete.get_search_string(TargetState(value, len(value))) == ""


@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform != "win32", reason="Need to be on Windows")
async def test_completion_displays_backslash_separator() -> None:
    class AutocompleteApp(App):
        def compose(self) -> ComposeResult:
            target = Input()
            yield target
            yield PathAutoCompleteInput(target)

    app = AutocompleteApp()
    async with app.run_test():
        target = app.query_one(Input)
        autocomplete = app.query_one(PathAutoCompleteInput)
        value = "C:/Users/ex"
        autocomplete.apply_completion("example\\", TargetState(value, len(value)))

        assert target.value == "C:\\Users\\example\\"
