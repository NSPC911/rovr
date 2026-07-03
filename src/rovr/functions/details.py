import stat
from datetime import datetime
from functools import lru_cache
from os import DirEntry, lstat
from typing import NamedTuple

from rich.cells import cell_len
from textual.widgets.option_list import Option

from rovr.functions.utils import natural_size
from rovr.variables.constants import config

try:
    from grp import getgrgid
    from pwd import getpwuid
except ImportError:  # windows
    getpwuid = None  # ty: ignore[invalid-assignment]
    getgrgid = None  # ty: ignore[invalid-assignment]

MIN_NAME_WIDTH = 20

DEFAULT_LABELS = {
    "size": "Size",
    "mtime": "Modified",
    "atime": "Accessed",
    "ctime": "Created",
    "permissions": "Permissions",
    "owner": "Owner",
    "group": "Group",
}


class DetailColumn(NamedTuple):
    type: str
    label: str
    width: int
    format: str


def _pad(value: str, width: int) -> str:
    """Right-align ``value`` into exactly ``width`` cells, truncating with an ellipsis.

    Returns:
        str: The padded (or truncated) value.
    """
    length = cell_len(value)
    if length > width:
        while value and cell_len(value) > width - 1:
            value = value[:-1]
        value += "…"
        length = cell_len(value)
    return " " * (width - length) + value


@lru_cache(maxsize=1)
def get_detail_columns() -> tuple[DetailColumn, ...]:
    # ponytail: cached once at first use; details_list is not hot-reloaded
    columns: list[DetailColumn] = []
    for entry in config["interface"]["details_list"]:
        column_type = entry["type"]
        if column_type not in DEFAULT_LABELS:
            continue
        label = entry.get("label", DEFAULT_LABELS[column_type])
        time_format = entry.get("format", config["metadata"]["datetime_format"])
        match column_type:
            case "size":
                natural_width = 7
            case "mtime" | "atime" | "ctime":
                natural_width = cell_len(datetime.now().strftime(time_format))
            case "permissions":
                natural_width = 10
            case _:  # owner/group
                natural_width = 8
        width = max(cell_len(label), entry.get("max_length", natural_width))
        columns.append(DetailColumn(column_type, label, width, time_format))
    return tuple(columns)


def fit_column_count(width: int, columns: tuple[DetailColumn, ...]) -> int:
    """How many leading columns fit, leaving the name at least MIN_NAME_WIDTH cells.

    Returns:
        int: The number of columns, from the start of the list, that fit.
    """
    available = width - MIN_NAME_WIDTH
    count = 0
    used = 0
    for column in columns:
        used += column.width + 2
        if used > available:
            break
        count += 1
    return count


@lru_cache(maxsize=512)
def _user_name(uid: int) -> str:
    if getpwuid is None:
        return "--"
    try:
        return getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


@lru_cache(maxsize=512)
def _group_name(gid: int) -> str:
    if getgrgid is None:
        return "--"
    try:
        return getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def detail_cells(
    dir_entry: DirEntry, option: Option, columns: tuple[DetailColumn, ...]
) -> tuple[str, ...]:
    """Format one fixed-width cell per configured column for a directory entry.

    Returns:
        tuple[str, ...]: One padded cell per column.
    """
    cells: list[str] = []
    for column in columns:
        try:
            file_stat = dir_entry.stat()
            match column.type:
                case "size":
                    if dir_entry.is_dir():
                        count = getattr(option, "folder_item_count", None)
                        value = "--" if count is None else str(count)
                    else:
                        value = natural_size(
                            file_stat.st_size,
                            "gnu",
                            config["metadata"]["filesize_decimals"],
                        )
                case "mtime":
                    value = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                        column.format
                    )
                case "atime":
                    value = datetime.fromtimestamp(file_stat.st_atime).strftime(
                        column.format
                    )
                case "ctime":
                    value = datetime.fromtimestamp(file_stat.st_ctime).strftime(
                        column.format
                    )
                case "permissions":
                    value = stat.filemode(lstat(dir_entry.path).st_mode)
                case "owner":
                    value = _user_name(file_stat.st_uid)
                case "group":
                    value = _group_name(file_stat.st_gid)
                case _:
                    value = "--"
        except (OSError, ValueError):
            value = "--"
        cells.append(_pad(value, column.width))
    return tuple(cells)
