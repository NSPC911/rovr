from rovr.functions import config, utils


def test_deep_merge() -> None:
    old = {"a": 1, "b": {"c": 2, "d": 3}}
    new = {"b": {"c": 20, "e": 4}, "f": 5}
    expected = {"a": 1, "b": {"c": 20, "d": 3, "e": 4}, "f": 5}
    result = config.deep_merge(old, new)
    assert result == expected


def test_deep_merge_prepend_list() -> None:
    old = {"items": [1, 2, 3]}
    new = {"prepend_items": [0]}
    result = config.deep_merge(old, new)
    assert result == {"items": [0, 1, 2, 3]}
    assert "prepend_items" not in result


def test_deep_merge_append_list() -> None:
    old = {"items": [1, 2, 3]}
    new = {"append_items": [4]}
    result = config.deep_merge(old, new)
    assert result == {"items": [1, 2, 3, 4]}
    assert "append_items" not in result


def test_deep_merge_prepend_append_with_override() -> None:
    old = {"items": [1, 2, 3]}
    new = {"items": [10], "prepend_items": [0], "append_items": [99]}
    result = config.deep_merge(old, new)
    assert result == {"items": [0, 10, 99]}


def test_deep_merge_prepend_append_nested() -> None:
    old = {"section": {"items": ["a", "b"]}}
    new = {"section": {"prepend_items": ["z"], "append_items": ["c"]}}
    result = config.deep_merge(old, new)
    assert result == {"section": {"items": ["z", "a", "b", "c"]}}


def test_deep_merge_prepend_nonexistent_base_ignored() -> None:
    old = {"a": 1}
    new = {"prepend_missing": ["x"]}
    result = config.deep_merge(old, new)
    assert result == {"a": 1}
    assert "prepend_missing" not in result


def test_deep_merge_append_bool_key_untouched() -> None:
    old = {"append_new_tabs": True}
    new = {"append_new_tabs": False}
    result = config.deep_merge(old, new)
    assert result == {"append_new_tabs": False}


def test_natural_size() -> None:
    assert utils.natural_size(1024, "binary", 2) == "1.00 KiB"
    assert utils.natural_size(1024, "decimal", 2) == "1.02 kB"
    assert utils.natural_size(1024, "gnu", 2) == "1.00K"
    assert utils.natural_size(123456789, "binary", 2) == "117.74 MiB"
    assert utils.natural_size(123456789, "decimal", 2) == "123.46 MB"
    assert utils.natural_size(123456789, "gnu", 2) == "117.74M"
