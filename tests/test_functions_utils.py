from rovr.functions import utils


def test_deep_merge() -> None:
    old = {"a": 1, "b": {"c": 2, "d": 3}}
    new = {"b": {"c": 20, "e": 4}, "f": 5}
    expected = {"a": 1, "b": {"c": 20, "d": 3, "e": 4}, "f": 5}
    result = utils.deep_merge(old, new)
    assert result == expected


def test_natural_size() -> None:
    assert utils.natural_size(1024, "binary", 2) == "1.00 KiB"
    assert utils.natural_size(1024, "decimal", 2) == "1.02 kB"
    assert utils.natural_size(1024, "gnu", 2) == "1.00K"
    assert utils.natural_size(123456789, "binary", 2) == "117.74 MiB"
    assert utils.natural_size(123456789, "decimal", 2) == "123.46 MB"
    assert utils.natural_size(123456789, "gnu", 2) == "117.74M"
