"""Test helpers and utilities for rovr tests."""

from typing import Any

from textual.pilot import Pilot


async def get_focused_widget(pilot: Pilot[Any]) -> Any:
    """Get the currently focused widget.

    Args:
        pilot: Textual test pilot instance

    Returns:
        The focused widget or None
    """
    return pilot.app.focused


async def press_keys(pilot: Pilot[Any], *keys: str) -> None:
    """Press multiple keys in sequence.

    Args:
        pilot: Textual test pilot instance
        *keys: Key names to press
    """
    for key in keys:
        await pilot.press(key)


async def type_text(pilot: Pilot[Any], text: str) -> None:
    """Type text character by character.

    Args:
        pilot: Textual test pilot instance
        text: Text to type
    """
    for char in text:
        await pilot.press(char)


def assert_widget_exists(app: Any, selector: str) -> None:
    """Assert that a widget matching the selector exists.

    Args:
        app: Textual app instance
        selector: CSS selector string
    """
    widgets = app.query(selector)
    assert len(widgets) > 0, f"No widget found matching '{selector}'"


def assert_widget_has_class(widget: Any, class_name: str) -> None:
    """Assert that a widget has a specific CSS class.

    Args:
        widget: Textual widget instance
        class_name: Expected class name
    """
    assert class_name in widget.classes, f"Widget missing class '{class_name}'"
