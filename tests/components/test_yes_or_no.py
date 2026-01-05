"""Tests for the YesOrNo modal screen."""

import pytest

from textual.app import App, ComposeResult
from textual.widgets import Button

from rovr.screens import YesOrNo


class YesOrNoTestApp(App):
    """Test harness app for YesOrNo screen."""

    def __init__(self, message: str = "Test?", **screen_kwargs):
        super().__init__()
        self.message = message
        self.screen_kwargs = screen_kwargs
        self.result = None

    def on_mount(self) -> None:
        def capture_result(result):
            self.result = result
            self.exit()

        self.push_screen(
            YesOrNo(message=self.message, **self.screen_kwargs),
            capture_result,
        )


class TestYesOrNoScreen:
    """Tests for YesOrNo modal dialog."""

    @pytest.mark.asyncio
    async def test_yes_button_returns_true(self):
        """Clicking Yes button returns True."""
        app = YesOrNoTestApp(message="Confirm action?")
        async with app.run_test() as pilot:
            await pilot.click("#yes")
        assert app.result is True

    @pytest.mark.asyncio
    async def test_no_button_returns_false(self):
        """Clicking No button returns False."""
        app = YesOrNoTestApp(message="Confirm action?")
        async with app.run_test() as pilot:
            await pilot.click("#no")
        assert app.result is False

    @pytest.mark.asyncio
    async def test_screen_displays_message(self):
        """Screen displays the provided message."""
        from textual.widgets import Label
        
        app = YesOrNoTestApp(message="Delete all files?")
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for screen to mount
            # Check message is displayed via labels
            labels = app.screen.query(Label)
            assert len(labels) > 0
            # Clean up
            await pilot.click("#no")

    @pytest.mark.asyncio
    async def test_multiline_message(self):
        """Multiline messages create multiple labels."""
        from textual.widgets import Label
        
        app = YesOrNoTestApp(message="Line 1\nLine 2\nLine 3")
        async with app.run_test() as pilot:
            await pilot.pause()
            # Each line becomes a label with .question class
            labels = app.screen.query(".question")
            assert len(labels) == 3
            await pilot.click("#no")

    @pytest.mark.asyncio
    async def test_with_toggle_returns_dict(self):
        """With toggle enabled, returns dict with value and toggle state."""
        app = YesOrNoTestApp(message="Delete?", with_toggle=True)
        async with app.run_test() as pilot:
            await pilot.click("#yes")
        assert isinstance(app.result, dict)
        assert "value" in app.result
        assert "toggle" in app.result
        assert app.result["value"] is True

    @pytest.mark.asyncio
    async def test_click_no_dismisses_with_false(self):
        """Clicking No dismisses with False."""
        app = YesOrNoTestApp(message="Confirm?")
        async with app.run_test() as pilot:
            await pilot.click("#no")
        assert app.result is False

    @pytest.mark.asyncio
    async def test_reverse_color_option(self):
        """reverse_color swaps button variants."""
        app = YesOrNoTestApp(message="Dangerous action?", reverse_color=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            yes_btn = app.screen.query_one("#yes", Button)
            no_btn = app.screen.query_one("#no", Button)
            # With reverse_color, Yes should be error variant
            assert yes_btn.variant == "error"
            assert no_btn.variant == "primary"
            await pilot.click("#no")
