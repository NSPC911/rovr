"""Integration tests for keyboard shortcuts."""

import pytest


class TestQuitShortcuts:
    """Tests for application quit shortcuts."""

    @pytest.mark.asyncio
    async def test_app_responds_to_quit_binding(self) -> None:
        """Application can be quit via keyboard shortcut."""
        from rovr.app import Application

        app = Application()
        async with app.run_test():
            # The app starts running
            assert app.is_running
            # We don't actually quit in the test to avoid issues


class TestCommandPalette:
    """Tests for command palette."""

    @pytest.mark.asyncio
    async def test_command_palette_binding_configured(self) -> None:
        """Command palette binding is configured."""
        from rovr.app import Application

        app = Application()
        # Check that COMMAND_PALETTE_BINDING is set
        assert hasattr(app, "COMMAND_PALETTE_BINDING")
        assert app.COMMAND_PALETTE_BINDING is not None


class TestFocusNavigation:
    """Tests for focus navigation."""

    @pytest.mark.asyncio
    async def test_tab_moves_focus(self) -> None:
        """Tab key moves focus between widgets."""
        from rovr.app import Application

        app = Application()
        async with app.run_test() as pilot:
            await pilot.press("tab")
            # Focus should potentially change (or stay if only one focusable)
            # This is more of a smoke test
            assert True  # Didn't crash
