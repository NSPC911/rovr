from rovr.functions.details import (
    MIN_NAME_WIDTH,
    DetailColumn,
    _pad,
    fit_column_count,
    parse_git_porcelain,
)

SIZE = DetailColumn("size", "Size", 7, "")
MTIME = DetailColumn("mtime", "Modified", 16, "")
GIT = DetailColumn("git", "Git", 3, "")


def test_pad_right_aligns() -> None:
    assert _pad("42K", 7) == "    42K"


def test_pad_width_equals_cell_len() -> None:
    # Width exactly matches the display width of the value: no padding or truncation.
    assert _pad("42K", 3) == "42K"


def test_pad_truncates_with_ellipsis() -> None:
    # When the width is smaller than the value, it should be truncated and end with an ellipsis.
    assert _pad("longvalue", 5) == "long…"


def test_pad_handles_wide_chars() -> None:
    # Wide characters should be measured by their display width, not code-point count.
    assert _pad("日本語", 6) == "日本語"
    assert _pad("日本語", 5) == "日本…"


def test_pad_width_zero_and_one() -> None:
    # Width 0 should produce an empty string; width 1 should still show an ellipsis.
    assert _pad("value", 0) == ""
    assert _pad("value", 1) == "…"


def test_pad_empty_string() -> None:
    # Empty values should still be padded to the requested width.
    assert _pad("", 0) == ""
    assert _pad("", 4) == "    "


def test_parse_git_porcelain_keeps_staged_and_unstaged_positions() -> None:
    output = b" M unstaged.py\x00M  staged.py\x00MM both.py\x00?? untracked.txt\x00"
    assert parse_git_porcelain(output, "") == {
        "unstaged.py": " M",
        "staged.py": "M ",
        "both.py": "MM",
        "untracked.txt": "??",
    }


def test_parse_git_porcelain_folder_aggregates_each_position() -> None:
    output = b"?? pkg/new.py\x00 M pkg/old.py\x00A  pkg/added.py\x00"
    assert parse_git_porcelain(output, "") == {"pkg": "AM"}


def test_parse_git_porcelain_respects_prefix() -> None:
    output = b" M sub/dir/file.py\x00 M elsewhere.py\x00?? sub/dir/nested/thing\x00"
    assert parse_git_porcelain(output, "sub/dir/") == {
        "file.py": " M",
        "nested": "??",
    }


def test_parse_git_porcelain_skips_rename_source() -> None:
    output = b"R  new_name.py\x00old_name.py\x00 M other.py\x00"
    assert parse_git_porcelain(output, "") == {
        "new_name.py": "R ",
        "other.py": " M",
    }


def test_fit_drops_trailing_columns_first() -> None:
    columns = (SIZE, MTIME, GIT)
    assert fit_column_count(200, columns) == 3
    # room for size + mtime but not git
    assert fit_column_count(20 + 9 + 18 + 2, columns) == 2
    # room for size only
    assert fit_column_count(20 + 9, columns) == 1
    # too narrow for anything
    assert fit_column_count(25, columns) == 0


def test_fit_exact_min_name_width_plus_one_column() -> None:
    # exact fit: name gutter at MIN_NAME_WIDTH plus one SIZE column including padding
    columns = (SIZE,)
    width = MIN_NAME_WIDTH + SIZE.width + 2
    assert fit_column_count(width, columns) == 1


def test_fit_just_below_min_name_width_returns_zero() -> None:
    # width just below MIN_NAME_WIDTH should result in 0 columns, even if the column itself would fit
    columns = (SIZE,)
    width = MIN_NAME_WIDTH - 1
    assert fit_column_count(width, columns) == 0
