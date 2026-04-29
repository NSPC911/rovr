import multiprocessing
import shlex
import subprocess
from contextlib import suppress
from shutil import which
from typing import Callable, Literal

from humanize import naturalsize
from textual import events
from textual.app import App, ScreenStackError
from textual.dom import DOMNode
from textual.message import Message
from textual.screen import Screen, ScreenResultType
from textual.worker import NoActiveWorker, WorkerCancelled, get_current_worker

from rovr import pprint
from rovr.classes.config import (
    _RovrConfigSettingsEditorBulkRename,
    _RovrConfigSettingsEditorFile,
    _RovrConfigSettingsEditorFolder,
)


def deep_merge(old: dict, new: dict) -> dict:
    """Mini lodash merge
    Args:
        old (dict): old dictionary
        new (dict): new dictionary, to merge on top of old

    Returns:
        dict: Merged dictionary
    """
    try:
        for key, value in new.items():
            if isinstance(value, dict):
                old[key] = deep_merge(old.get(key, {}), value)
            else:
                old[key] = value
    except Exception as exc:
        pprint(
            f"While deep merging the default config with the userconfig, {type(exc).__name__} was raised.\n    {exc}\nSince the conflict cannot be resolved, rovr will not be launching."
        )
        exit(1)
    return old


def set_scuffed_subtitle(element: DOMNode, *sections: str) -> None:
    """The most scuffed way to display a custom subtitle

    Args:
        element (Widget): The element containing style information.
        *sections (str): The sections to display
    """
    from rovr.variables.maps import BORDER_BOTTOM

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


def natural_size(
    integer: int, suffix: Literal["gnu", "binary", "decimal"], filesize_decimals: int
) -> str:
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
        case "decimal":
            return naturalsize(value=integer, format=f"%.{filesize_decimals}f")


def is_being_used(exc: OSError) -> bool:
    """
    On Windows, a file being used by another process raises a PermissionError/OSError with winerror 32.
    Args:
        exc(OSError): the OSError object

    Returns:
        bool: whether it is due to the file being used
    """
    # 32: Used by another process
    # 145: Access is denied
    return getattr(exc, "winerror", None) in (5, 13, 32, 145)


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


def check_key(event: events.Key, key_list: list[str] | str) -> bool:
    if isinstance(key_list, str):
        key_list = [key_list]
    return bool(
        # check key
        event.key in key_list
        # check aliases
        or any(key in key_list for key in event.aliases)
        # check character
        or event.is_printable
        and event.character in key_list
    )


def is_archive(path_str: str) -> bool:
    from rovr.classes.archive import Archive

    try:
        with Archive(path_str) as _:
            return True
    except Exception:
        return False


def get_shortest_bind(binds: list[str]) -> str:
    least_len: tuple[int | None, str] = (None, "")
    for bind in binds:
        if least_len[0] is None or least_len[0] > len(bind):
            least_len = (len(bind), bind)
    return least_len[1]


def run_editor_command(
    app: DOMNode,
    editor_config: _RovrConfigSettingsEditorFile
    | _RovrConfigSettingsEditorFolder
    | _RovrConfigSettingsEditorBulkRename,
    target_path: str,
    on_error: Callable[[str, str], None] | None = None,
) -> subprocess.CompletedProcess | None:
    """Run an editor command based on configuration.

    Args:
        app: The Textual app instance (needed for suspend/run_in_thread).
        editor_config: Configuration dict with 'run', 'suspend', and optionally 'block' keys.
        target_path: The file/folder path to open in the editor.
        on_error: Optional callback for error handling, receives (message, title).

    Returns:
        CompletedProcess if command was run synchronously, None if run in thread.
    """
    command = shlex.split(editor_config["run"]) + [target_path]
    # expand first part because path
    command = [which(command[0])] + command[1:]

    if editor_config.get("suspend", False):
        with app.suspend():
            process = subprocess.run(command)
        if process.returncode != 0 and on_error:
            on_error(f"Error Code {process.returncode}", "Editor Error")
        return process
    elif editor_config.get("block", False):
        process = subprocess.run(command, capture_output=True)
        if process.returncode != 0 and on_error:
            on_error(process.stderr.decode(), f"Error Code {process.returncode}")
        return process
    else:
        app.run_in_thread(subprocess.run, command, capture_output=True)
        return None


def dismiss(
    screen: Screen, result: ScreenResultType | None = None, event: Message | None = None
) -> None:
    if event is not None:
        event.prevent_default()
        event.stop()
        event._set_forwarded()

    if screen in screen.app.screen_stack:
        with suppress(ScreenStackError):
            screen.dismiss(result)


def multiprocessing_process_error_checker(app: App, exc: Exception) -> bool:
    if isinstance(exc, ValueError) and "fds_to_keep" in str(exc):
        match multiprocessing.get_start_method(allow_none=True):
            case None:
                # try forkserver
                try:
                    multiprocessing.set_start_method("forkserver")
                    app.notify("multiprocessing is now using forkserver")
                except ValueError as val_exc:
                    if "cannot find context" in str(val_exc):
                        multiprocessing.set_start_method("spawn")
                        app.notify("multiprocessing is now using spawn")
            case "fork":  # theoretically this shouldn't happen
                multiprocessing.set_start_method("forkserver")
                app.notify("multiprocessing is now using forkserver")
            case "forkserver":
                multiprocessing.set_start_method("spawn")
                app.notify("multiprocessing is now using spawn")
            case "spawn":
                # nothing else we can do, except forcefully stop using Process
                app.MULTIPROCESSING_PROCESS_ALLOWED = False
        return True
    return False
