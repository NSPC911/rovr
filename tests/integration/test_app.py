"""Integration tests for the main Application."""

import pytest


class TestApplicationStartup:
    """Tests for application lifecycle."""

    @pytest.mark.asyncio
    async def test_app_starts(self) -> None:
        """Application starts without errors."""
        from rovr.app import Application

        app = Application()
        async with app.run_test():
            assert app.is_running

    @pytest.mark.asyncio
    async def test_app_has_file_list(self) -> None:
        """Application contains a FileList widget."""
        from rovr.app import Application
        from rovr.core import FileList

        app = Application()
        async with app.run_test():
            file_lists = app.query(FileList)
            assert len(file_lists) > 0

    @pytest.mark.asyncio
    async def test_app_has_header(self) -> None:
        """Application contains header area."""
        from rovr.app import Application
        from rovr.header import HeaderArea

        app = Application()
        async with app.run_test():
            headers = app.query(HeaderArea)
            assert len(headers) > 0

    @pytest.mark.asyncio
    async def test_app_has_footer_components(self) -> None:
        """Application contains footer components."""
        from rovr.app import Application
        from rovr.footer import MetadataContainer, ProcessContainer

        app = Application()
        async with app.run_test():
            metadata = app.query(MetadataContainer)
            process = app.query(ProcessContainer)

            assert len(metadata) > 0, "No MetadataContainer found"
            assert len(process) > 0, "No ProcessContainer found"

    @pytest.mark.asyncio
    async def test_app_loads_css(self) -> None:
        """Application loads CSS stylesheets."""
        from rovr.app import Application

        app = Application()
        async with app.run_test():
            # CSS_PATH should be set
            assert hasattr(app, "CSS_PATH")
            assert len(app.CSS_PATH) > 0

    @pytest.mark.asyncio
    async def test_app_has_bindings(self) -> None:
        """Application has keybindings configured."""
        from rovr.app import Application

        app = Application()
        async with app.run_test():
            # BINDINGS should be set
            assert hasattr(app, "BINDINGS")
            assert len(app.BINDINGS) > 0


class TestApplicationComponents:
    """Tests for application component integration."""

    @pytest.mark.asyncio
    async def test_all_core_components_present(self) -> None:
        """All core components are present in the app."""
        from rovr.app import Application
        from rovr.core import (
            FileList,
            FileListContainer,
            PinnedSidebar,
            PreviewContainer,
        )
        from rovr.footer import Clipboard, MetadataContainer
        from rovr.header import HeaderArea

        app = Application()
        async with app.run_test():
            # Core components
            assert len(app.query(FileList)) > 0, "Missing FileList"
            assert len(app.query(FileListContainer)) > 0, "Missing FileListContainer"
            assert len(app.query(PreviewContainer)) > 0, "Missing PreviewContainer"
            assert len(app.query(PinnedSidebar)) > 0, "Missing PinnedSidebar"

            # Header/Footer
            assert len(app.query(HeaderArea)) > 0, "Missing HeaderArea"
            assert len(app.query(Clipboard)) > 0, "Missing Clipboard"
            assert len(app.query(MetadataContainer)) > 0, "Missing MetadataContainer"

    @pytest.mark.asyncio
    async def test_action_buttons_present(self) -> None:
        """Action buttons are present in the app."""
        from rovr.action_buttons import (
            CopyButton,
            CutButton,
            DeleteButton,
            PasteButton,
        )
        from rovr.app import Application

        app = Application()
        async with app.run_test():
            # Check for main action buttons
            assert len(app.query(CopyButton)) > 0, "Missing CopyButton"
            assert len(app.query(CutButton)) > 0, "Missing CutButton"
            assert len(app.query(PasteButton)) > 0, "Missing PasteButton"
            assert len(app.query(DeleteButton)) > 0, "Missing DeleteButton"
