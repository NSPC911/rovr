from rovr.functions.details import DetailColumn, _pad, fit_column_count

SIZE = DetailColumn("size", "Size", 7, "")
MTIME = DetailColumn("mtime", "Modified", 16, "")
GIT = DetailColumn("git", "Git", 3, "")


def test_pad_right_aligns() -> None:
    assert _pad("42K", 7) == "    42K"


def test_pad_truncates_with_ellipsis() -> None:
    assert _pad("longvalue", 5) == "long…"


def test_pad_handles_wide_chars() -> None:
    assert _pad("日本語", 6) == "日本語"
    assert _pad("日本語", 5) == "日本…"


def test_fit_drops_trailing_columns_first() -> None:
    columns = (SIZE, MTIME, GIT)
    assert fit_column_count(200, columns) == 3
    # room for size + mtime but not git
    assert fit_column_count(20 + 9 + 18 + 2, columns) == 2
    # room for size only
    assert fit_column_count(20 + 9, columns) == 1
    # too narrow for anything
    assert fit_column_count(25, columns) == 0
