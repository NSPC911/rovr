import os
import tempfile
from contextlib import suppress
from os import path
from typing import Any, Dict

import ujson

from rovr.functions.utils import pprint
from rovr.variables.maps import VAR_TO_DIR


class UIStateManager:
    """Manages persistent UI state across application sessions."""

    DEFAULT_STATE = {
        "footer_visible": True,
        "pinned_sidebar_visible": True,
        "preview_sidebar_visible": True,
        "show_hidden_files": False,
    }

    def __init__(self) -> None:
        self.state_file = path.join(VAR_TO_DIR["CONFIG"], "ui_state.json")
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load UI state from file, with fallback to defaults.

        Returns:
            Dict[str, Any]: The loaded UI state merged with defaults.
        """
        try:
            if path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    loaded_state = ujson.load(f)

                # Validate loaded state and merge with defaults
                if isinstance(loaded_state, dict):
                    # Merge with defaults to handle missing keys
                    merged_state = self.DEFAULT_STATE.copy()
                    merged_state.update(loaded_state)
                    return merged_state
                else:
                    pprint(
                        "[bright_yellow]Warning:[/] Invalid UI state format, using defaults"
                    )
            else:
                pprint(
                    "[bright_blue]Info:[/] UI state file not found, creating with defaults"
                )
        except (OSError, ValueError, ujson.JSONDecodeError) as e:
            pprint(
                f"[bright_yellow]Warning:[/] Failed to load UI state ({e}), using defaults"
            )

        return self.DEFAULT_STATE.copy()

    def _save_state(self) -> None:
        """Save current UI state to file."""
        try:
            # Ensure config directory exists
            config_dir = VAR_TO_DIR["CONFIG"]
            if not path.exists(config_dir):
                os.makedirs(config_dir)

            # Write to a temporary file first, then atomically replace
            fd, temp_path = tempfile.mkstemp(
                dir=config_dir, prefix=".ui_state_", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    ujson.dump(self._state, f, indent=2)
                # Atomic replace (even on Windows with Python 3.3+)
                os.replace(temp_path, self.state_file)
            except Exception:
                # Clean up temp file if anything goes wrong
                with suppress(OSError):
                    os.unlink(temp_path)
                raise
        except OSError as e:
            pprint(f"[bright_red]Error:[/] Failed to save UI state: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current UI state.

        Returns:
            Dict[str, Any]: A copy of the current UI state.
        """
        return self._state.copy()

    def update_state(self, key: str, value: object) -> None:
        """Update a single state value and save."""
        if key in self.DEFAULT_STATE:
            self._state[key] = value
            self._save_state()
        else:
            pprint(f"[bright_yellow]Warning:[/] Unknown UI state key: {key}")

    def reset_to_defaults(self) -> None:
        """Reset UI state to defaults."""
        self._state = self.DEFAULT_STATE.copy()
        self._save_state()


# Global instance
ui_state_manager = UIStateManager()


def get_ui_state() -> Dict[str, Any]:
    """Get current UI state.

    Returns:
        Dict[str, Any]: A copy of the current UI state.
    """
    return ui_state_manager.get_state()


def update_ui_state(key: str, value: object) -> None:
    """Update UI state and persist it."""
    ui_state_manager.update_state(key, value)


def reset_ui_state() -> None:
    """Reset UI state to defaults."""
    ui_state_manager.reset_to_defaults()
