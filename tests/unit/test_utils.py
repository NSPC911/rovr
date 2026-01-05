"""Unit tests for rovr.functions.utils module."""

import pytest

from rovr.functions.utils import (
    deep_merge,
    natural_size,
    check_key,
    get_shortest_bind,
)


class TestDeepMerge:
    """Tests for the deep_merge function."""

    def test_simple_merge(self):
        """Merging flat dictionaries."""
        old = {"a": 1, "b": 2}
        new = {"b": 3, "c": 4}
        result = deep_merge(old, new)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Merging nested dictionaries."""
        old = {"outer": {"a": 1, "b": 2}}
        new = {"outer": {"b": 3, "c": 4}}
        result = deep_merge(old, new)
        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_deep_nested_merge(self):
        """Merging deeply nested structures."""
        old = {"l1": {"l2": {"l3": {"a": 1}}}}
        new = {"l1": {"l2": {"l3": {"b": 2}}}}
        result = deep_merge(old, new)
        assert result == {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}}

    def test_new_overwrites_value_same_type(self):
        """New value of same type replaces old value."""
        old = {"key": "old_string"}
        new = {"key": "new_string"}
        result = deep_merge(old, new)
        assert result == {"key": "new_string"}

    def test_list_values_replaced(self):
        """List values are replaced, not merged."""
        old = {"items": [1, 2, 3]}
        new = {"items": [4, 5]}
        result = deep_merge(old, new)
        assert result == {"items": [4, 5]}

    def test_empty_dicts(self):
        """Merging with empty dictionaries."""
        assert deep_merge({}, {"a": 1}) == {"a": 1}
        assert deep_merge({"a": 1}, {}) == {"a": 1}


class TestNaturalSize:
    """Tests for the natural_size function."""

    def test_decimal_format(self):
        """Test decimal (SI) size formatting."""
        result = natural_size(1000, "decimal", 1)
        assert "1" in result and "k" in result.lower()

    def test_binary_format(self):
        """Test binary (IEC) size formatting."""
        result = natural_size(1024, "binary", 1)
        assert "1" in result

    def test_gnu_format(self):
        """Test GNU-style size formatting."""
        result = natural_size(1024, "gnu", 0)
        assert "1" in result

    def test_zero_bytes(self):
        """Zero bytes should format correctly."""
        result = natural_size(0, "decimal", 0)
        assert "0" in result


class TestCheckKey:
    """Tests for the check_key function."""

    def test_key_in_list(self):
        """Key matches when in the list."""
        class MockEvent:
            key = "a"
            aliases = []
            is_printable = True
            character = "a"
        
        assert check_key(MockEvent(), ["a", "b", "c"]) is True

    def test_key_not_in_list(self):
        """Key doesn't match when not in list."""
        class MockEvent:
            key = "x"
            aliases = []
            is_printable = True
            character = "x"
        
        assert check_key(MockEvent(), ["a", "b", "c"]) is False

    def test_alias_matches(self):
        """Key matches via alias."""
        class MockEvent:
            key = "enter"
            aliases = ["return", "ctrl+m"]
            is_printable = False
            character = None
        
        assert check_key(MockEvent(), ["return"]) is True

    def test_string_key_list(self):
        """Single string is treated as list."""
        class MockEvent:
            key = "q"
            aliases = []
            is_printable = True
            character = "q"
        
        assert check_key(MockEvent(), "q") is True


class TestGetShortestBind:
    """Tests for the get_shortest_bind function."""

    def test_returns_shortest(self):
        """Returns the shortest keybind."""
        assert get_shortest_bind(["ctrl+shift+a", "ctrl+a", "a"]) == "a"

    def test_single_item(self):
        """Single item list returns that item."""
        assert get_shortest_bind(["escape"]) == "escape"

    def test_empty_list(self):
        """Empty list returns empty string."""
        assert get_shortest_bind([]) == ""

    def test_equal_length(self):
        """Equal length returns one of them."""
        result = get_shortest_bind(["ab", "cd", "ef"])
        assert result in ["ab", "cd", "ef"]
        assert len(result) == 2
