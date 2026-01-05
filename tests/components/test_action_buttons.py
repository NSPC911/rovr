"""Tests for action button components."""

import pytest

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button

from rovr.action_buttons import (
    CopyButton,
    CutButton,
    PasteButton,
    DeleteButton,
)


class ActionButtonTestApp(App):
    """Test harness for action buttons."""
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield CopyButton()
            yield CutButton()
            yield PasteButton()
            yield DeleteButton()


class TestCopyButton:
    """Tests for CopyButton component."""

    @pytest.mark.asyncio
    async def test_button_renders(self):
        """CopyButton renders without errors."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#copy", Button)
            assert button is not None

    @pytest.mark.asyncio
    async def test_button_has_option_class(self):
        """CopyButton has 'option' CSS class."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#copy", Button)
            assert "option" in button.classes

    @pytest.mark.asyncio
    async def test_button_has_icon(self):
        """CopyButton displays an icon."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#copy", Button)
            # Button should have some label (the icon)
            assert button.label is not None
            assert len(str(button.label)) > 0


class TestCutButton:
    """Tests for CutButton component."""

    @pytest.mark.asyncio
    async def test_button_renders(self):
        """CutButton renders without errors."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#cut", Button)
            assert button is not None

    @pytest.mark.asyncio
    async def test_button_has_option_class(self):
        """CutButton has 'option' CSS class."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#cut", Button)
            assert "option" in button.classes


class TestPasteButton:
    """Tests for PasteButton component."""

    @pytest.mark.asyncio
    async def test_button_renders(self):
        """PasteButton renders without errors."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#paste", Button)
            assert button is not None


class TestDeleteButton:
    """Tests for DeleteButton component."""

    @pytest.mark.asyncio
    async def test_button_renders(self):
        """DeleteButton renders without errors."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#delete", Button)
            assert button is not None

    @pytest.mark.asyncio
    async def test_button_has_correct_id(self):
        """DeleteButton has 'delete' id."""
        app = ActionButtonTestApp()
        async with app.run_test() as pilot:
            button = app.query_one("#delete", Button)
            assert button.id == "delete"
