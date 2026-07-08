import stat
from datetime import datetime
from functools import lru_cache
from os import DirEntry, lstat, stat_result
from subprocess import TimeoutExpired, run
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
    "git": "Git",
}

# most severe first; a folder shows the most severe status found beneath it
_GIT_SEVERITY = "UDMRCA?"


class DetailColumn(NamedTuple):
    type: str
    label: str
    width: int
    format: str


def _pad(value: str, width: int) -> str:
    """Right-align `value` into exactly `width` cells, truncating with an ellipsis.

    Returns:
        str: The padded (or truncated) value.
    """
    if width <= 0:
        return ""
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
            case "git":
                natural_width = 2
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


def _worst_git_char(*candidates: str) -> str:
    worst = ""
    for candidate in candidates:
        for char in candidate:
            if char in _GIT_SEVERITY and (
                not worst or _GIT_SEVERITY.index(char) < _GIT_SEVERITY.index(worst)
            ):
                worst = char
    return worst


def parse_git_porcelain(output: bytes, prefix: str) -> dict[str, str]:
    """Map each top-level name under `prefix` to its git XY status pair.

    Like `git status --short`: the first char is the staged (index) status,
    the second the unstaged (work tree) status. Folders aggregate each
    position independently to the most severe char found beneath them.

    Args:
        output: Raw `git status --porcelain -z` output.
        prefix: The cwd relative to the repository root (`git rev-parse --show-prefix`).

    Returns:
        dict[str, str]: Name in cwd -> two chars of UDMRCA? (space = clean).
    """
    statuses: dict[str, str] = {}
    entries = output.decode(errors="replace").split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        xy, rel_path = entry[:2], entry[3:]
        if xy[0] in "RC":
            index += 1  # skip the rename/copy source path
        if not rel_path.startswith(prefix):
            continue
        name = rel_path[len(prefix) :].split("/", 1)[0]
        if name:
            existing = statuses.get(name, "  ")
            statuses[name] = (_worst_git_char(xy[0], existing[0]) or " ") + (
                _worst_git_char(xy[1], existing[1]) or " "
            )
    return statuses


def git_statuses(cwd: str) -> dict[str, str] | None:
    """Git status chars for every changed entry directly inside `cwd`.

    Returns:
        dict[str, str]: Name in cwd -> two chars of UDMRCA? (space = clean).
        None if cwd is not a git repository or git is unavailable.
    """
    try:
        prefix_proc = run(
            ["git", "-C", cwd, "rev-parse", "--show-prefix"],
            capture_output=True,
            timeout=5,
        )
        if prefix_proc.returncode != 0:
            return None
        status_proc = run(
            ["git", "-C", cwd, "status", "--porcelain", "-z", "."],
            capture_output=True,
            timeout=10,
        )
        if status_proc.returncode != 0:
            return None
    except (OSError, TimeoutExpired):
        return None
    prefix = prefix_proc.stdout.decode(errors="replace").strip()
    return parse_git_porcelain(status_proc.stdout, prefix)


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
    try:
        file_stat = dir_entry.stat()
    except OSError:
        file_stat = None
    lstats: stat_result | None = None
    for column in columns:
        try:
            match column.type:
                case "size":
                    if dir_entry.is_dir():
                        count = getattr(option, "folder_item_count", None)
                        value = "--" if count is None else str(count)
                    elif file_stat is None:
                        value = "--"
                    else:
                        value = natural_size(
                            file_stat.st_size,
                            config["metadata"]["filesize_suffix"],
                            config["metadata"]["filesize_decimals"],
                        )
                case "mtime":
                    value = (
                        datetime.fromtimestamp(file_stat.st_mtime).strftime(
                            column.format
                        )
                        if file_stat
                        else "--"
                    )
                case "atime":
                    value = (
                        datetime.fromtimestamp(file_stat.st_atime).strftime(
                            column.format
                        )
                        if file_stat
                        else "--"
                    )
                case "ctime":
                    value = (
                        datetime.fromtimestamp(file_stat.st_ctime).strftime(
                            column.format
                        )
                        if file_stat
                        else "--"
                    )
                case "permissions":
                    if not lstats:
                        lstats = lstat(dir_entry.path)
                    value = stat.filemode(lstats.st_mode)
                case "owner":
                    value = _user_name(file_stat.st_uid) if file_stat else "--"
                case "group":
                    value = _group_name(file_stat.st_gid) if file_stat else "--"
                case "git":
                    value = getattr(option, "git_status", "")
                case _:
                    value = "--"
        except (OSError, ValueError):
            value = "--"
        cells.append(_pad(value, column.width))
    return tuple(cells)
