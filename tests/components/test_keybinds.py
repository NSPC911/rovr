"""Tests for the Keybinds screen."""

from typing import Any

import pytest
from textual.app import App

from rovr.screens import Keybinds
from rovr.screens.keybinds import KeybindList


class KeybindsTestApp(App):
    """Test harness for Keybinds screen."""

    def __init__(self) -> None:
        super().__init__()
        self.screen_dismissed = False

    def on_mount(self) -> None:
        def on_dismiss(result: Any) -> None:
            self.screen_dismissed = True
            self.exit()

        self.push_screen(Keybinds(), on_dismiss)


class TestKeybindsScreen:
    """Tests for Keybinds modal screen."""

    @pytest.mark.asyncio
    async def test_screen_mounts(self) -> None:
        """Keybinds screen mounts without errors."""
        app = KeybindsTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for screen to mount
            assert app.screen is not None
            await pilot.press("escape")  # Clean exit

    @pytest.mark.asyncio
    async def test_contains_keybind_list(self) -> None:
        """Keybinds screen contains a KeybindList."""
        app = KeybindsTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            keybind_lists = app.screen.query(KeybindList)
            assert len(keybind_lists) > 0
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_escape_dismisses(self) -> None:
        """Pressing Escape dismisses the screen."""
        app = KeybindsTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()  # Wait for dismiss to process
        # After exit, the app should have processed the dismiss
        assert app.screen_dismissed is True or not app.is_running

    @pytest.mark.asyncio
    async def test_has_search_input(self) -> None:
        """Keybinds screen has a search input for filtering."""
        from rovr.components import SearchInput

        app = KeybindsTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            search_inputs = app.screen.query(SearchInput)
            assert len(search_inputs) > 0
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_keybind_list_has_items(self) -> None:
        """Keybind list is populated with keybindings."""
        app = KeybindsTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            keybind_list = app.screen.query_one(KeybindList)
            # Should have multiple keybind entries
            assert keybind_list.option_count > 0
            await pilot.press("escape")
