"""Integration tests for state management."""

from typing import Any, get_args

import pytest


class TestStateManager:
    """Tests for StateManager component."""

    @pytest.mark.asyncio
    async def test_state_manager_exists(self, app: Any) -> None:
        """Application has exactly one StateManager."""
        from rovr.state_manager import StateManager

        async with app.run_test():
            state_managers = app.query(StateManager)
            assert len(state_managers) == 1

    @pytest.mark.asyncio
    async def test_state_manager_has_sort_by(self, app: Any) -> None:
        """StateManager has sort_by property with valid option."""
        from rovr.state_manager import StateManager
        from rovr.variables.constants import SortByOptions

        async with app.run_test():
            state_manager = app.query_one(StateManager)
            assert hasattr(state_manager, "sort_by")
            # Use get_args to extract valid options from the type alias (DRY)
            valid_options = get_args(SortByOptions)
            assert state_manager.sort_by in valid_options
