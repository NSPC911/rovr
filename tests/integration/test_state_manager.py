"""Integration tests for state management."""

import pytest


class TestStateManager:
    """Tests for StateManager component."""

    @pytest.mark.asyncio
    async def test_state_manager_exists(self):
        """Application has a StateManager."""
        from rovr.app import Application
        from rovr.state_manager import StateManager
        
        app = Application()
        async with app.run_test() as pilot:
            state_managers = app.query(StateManager)
            assert len(state_managers) > 0

    @pytest.mark.asyncio
    async def test_state_manager_has_sort_by(self):
        """StateManager has sort_by property."""
        from rovr.app import Application
        from rovr.state_manager import StateManager
        
        app = Application()
        async with app.run_test() as pilot:
            state_manager = app.query_one(StateManager)
            assert hasattr(state_manager, "sort_by")
            # sort_by should be a valid option
            valid_options = ["name", "size", "modified", "created", "extension", "natural"]
            assert state_manager.sort_by in valid_options
