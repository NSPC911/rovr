"""Integration tests for file operations."""

import pytest
from pathlib import Path


class TestClipboard:
    """Tests for clipboard operations."""

    @pytest.mark.asyncio
    async def test_clipboard_widget_exists(self):
        """Application has a clipboard widget."""
        from rovr.app import Application
        from rovr.footer import Clipboard
        
        app = Application()
        async with app.run_test() as pilot:
            clipboards = app.query(Clipboard)
            assert len(clipboards) > 0


class TestPreviewContainer:
    """Tests for file preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_container_exists(self):
        """Application has a preview container."""
        from rovr.app import Application
        from rovr.core import PreviewContainer
        
        app = Application()
        async with app.run_test() as pilot:
            previews = app.query(PreviewContainer)
            assert len(previews) > 0


class TestSidebar:
    """Tests for pinned sidebar."""

    @pytest.mark.asyncio
    async def test_pinned_sidebar_exists(self):
        """Application has a pinned sidebar."""
        from rovr.app import Application
        from rovr.core import PinnedSidebar
        
        app = Application()
        async with app.run_test() as pilot:
            sidebars = app.query(PinnedSidebar)
            assert len(sidebars) > 0
