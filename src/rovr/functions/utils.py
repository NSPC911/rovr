from humanize import naturalsize
from lzstring import LZString
from rich.console import Console
from textual.dom import DOMNode
from textual.worker import NoActiveWorker, WorkerCancelled, get_current_worker

from rovr.variables.maps import (
    BORDER_BOTTOM,
)

lzstring = LZString()
pprint = Console().print


def deep_merge(d: dict, u: dict) -> dict:
    """Mini lodash merge
    Args:
        d (dict): old dictionary
        u (dict): new dictionary, to merge on top of d

    Returns:
        dict: Merged dictionary
    """
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = deep_merge(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def set_nested_value(d: dict, path_str: str, value: bool) -> None:
    """Sets a value in a nested dictionary using a dot-separated path string.

    Args:
        d (dict): The dictionary to modify.
        path_str (str): The dot-separated path to the key (e.g., "plugins.bat").
        value (bool): The value to set. (boolean for now)
    """
    keys = path_str.split(".")
    current = d
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            try:
                if isinstance(current[key], dict) and "enabled" in current[key]:
                    current[key]["enabled"] = value
                elif type(current[key]) is type(value):
                    current[key] = value
                else:
                    pprint("[bright_red underline]Config Error:[/]")
                    pprint(
                        f"[cyan bold]{path_str}[/]'s new value of type [cyan b]{type(value).__name__}[/] is not a [bold cyan]{type(current[key]).__name__}[/] type, and cannot be modified."
                    )
                    exit(1)
            except KeyError:
                pprint("[bright_red underline]Config Error:[/]")
                pprint(
                    f"[cyan b]{path_str}[/] is not a valid path to an existing value and hence cannot be set."
                )
                exit(1)
        else:
            if not isinstance(current.get(key), dict):
                current[key] = {}
            current = current[key]


def set_scuffed_subtitle(element: DOMNode, *sections: str) -> None:
    """The most scuffed way to display a custom subtitle

    Args:
        element (Widget): The element containing style information.
        *sections (str): The sections to display
    """
    try:
        border_bottom = BORDER_BOTTOM.get(
            element.styles.border_bottom[0], BORDER_BOTTOM["blank"]
        )
    except AttributeError:
        border_bottom = BORDER_BOTTOM["blank"]
    subtitle = ""
    for index, section in enumerate(sections):
        subtitle += section
        if index + 1 != len(sections):
            subtitle += " "
            subtitle += (
                border_bottom if element.app.ansi_color else f"[r]{border_bottom}[/]"
            )
            subtitle += " "

    element.border_subtitle = subtitle


def natural_size(integer: int, suffix: str, filesize_decimals: int) -> str:
    assert suffix in ["decimal", "binary", "gnu"]
    match suffix:
        case "gnu":
            return naturalsize(
                value=integer,
                gnu=True,
                format=f"%.{filesize_decimals}f",
            )
        case "binary":
            return naturalsize(
                value=integer,
                binary=True,
                format=f"%.{filesize_decimals}f",
            )
        case _:
            return naturalsize(value=integer, format=f"%.{filesize_decimals}f")


def should_cancel() -> bool:
    """
    Whether the current worker should cancel execution

    Returns:
        bool: whether to cancel this worker or not
    """
    try:
        worker = get_current_worker()
    except RuntimeError:
        return False
    except WorkerCancelled:
        return True
    except NoActiveWorker:
        return False
    return bool(worker and not worker.is_running)
