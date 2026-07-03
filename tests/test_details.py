from rovr.functions.details import (
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


def test_pad_truncates_with_ellipsis() -> None:
    assert _pad("longvalue", 5) == "long…"


def test_pad_handles_wide_chars() -> None:
    assert _pad("日本語", 6) == "日本語"
    assert _pad("日本語", 5) == "日本…"


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
