import multiprocessing
import os
import re
import subprocess
from contextlib import suppress
from functools import lru_cache
from typing import Callable, Literal

from humanize import naturalsize
from textual import events
from textual.app import App, ScreenStackError
from textual.dom import DOMNode
from textual.message import Message
from textual.screen import Screen, ScreenResultType
from textual.worker import NoActiveWorker, WorkerCancelled, get_current_worker


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
    Args:
        exc(OSError): the OSError object

    Returns:
        bool: whether it is due to the file being used
    """

    # This is genuinely pissing me off so much, I keep getting false positives, so you know what
    # I will check whether the exception's strerror matches the full sentence
    return "being used by another process" in str(exc.strerror)


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
    if not os.path.isfile(path_str):
        return False

    from multiarchive import Archive

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


def run_command(
    app: App,
    command: str | list[str],
    run_type: Literal["suspend", "background", "orphan"],
    shell: bool = True,
    on_error: Callable[[str, str], None] | None = None,
) -> subprocess.CompletedProcess | subprocess.Popen:
    if shell and isinstance(command, list):
        from shlex import join

        command = join(command)
    elif not shell and isinstance(command, str):
        from shlex import split

        command = split(command)

    match run_type:
        case "orphan":
            import sys

            if sys.platform == "win32":
                return subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.DETACHED_PROCESS,
                    shell=shell,
                )
            else:
                return subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                    shell=shell,
                )
        case "background":
            return subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
            )
        case "suspend":

            def func() -> subprocess.CompletedProcess:
                with app.suspend():
                    if globals().get("is_dev", False):
                        print(command)
                    return subprocess.run(command, shell=shell)

            try:
                process = app.call_from_thread(func)
            except RuntimeError:
                process = func()
            if process.returncode != 0 and on_error:
                on_error(f"Error Code {process.returncode}", "Editor Error")
            return process
        case _:
            from typing import assert_never

            assert_never(run_type)


def dismiss(
    screen: Screen, result: ScreenResultType | None = None, event: Message | None = None
) -> None:
    if event is not None:
        event.prevent_default().stop()._set_forwarded()

    if screen in screen.app.screen_stack:
        with suppress(ScreenStackError):
            screen.dismiss(result)


def multiprocessing_process_error_checker(app: App, exc: Exception) -> bool:
    if isinstance(exc, ValueError) and "fds_to_keep" in str(exc):
        match multiprocessing.get_start_method(allow_none=True):
            case None:
                # try forkserver
                try:
                    multiprocessing.set_start_method("forkserver", force=True)
                    app.notify("multiprocessing is now using forkserver")
                except ValueError as val_exc:
                    if "cannot find context" in str(val_exc):
                        multiprocessing.set_start_method("spawn", force=True)
                        app.notify("multiprocessing is now using spawn")
            case "fork":  # theoretically this shouldn't happen
                multiprocessing.set_start_method("forkserver", force=True)
                app.notify("multiprocessing is now using forkserver")
            case "forkserver":
                multiprocessing.set_start_method("spawn", force=True)
                app.notify("multiprocessing is now using spawn")
            case "spawn":
                # nothing else we can do, except forcefully stop using Process
                app.MULTIPROCESSING_PROCESS_ALLOWED = False
        return True
    return False


async def expand_command(app: App, command: str) -> str:
    from rovr.functions.path import normalise

    cwd = normalise(os.getcwd())
    highlighted = ""
    if app.file_list.highlighted_option is not None and hasattr(
        app.file_list.highlighted_option, "dir_entry"
    ):
        highlighted = normalise(app.file_list.highlighted_option.dir_entry.path)

    selected_files = await app.file_list.get_selected_objects() or []

    expanded = command.replace("${current_working_directory}", cwd)
    expanded = expanded.replace("${highlighted_file}", highlighted)
    if selected_files:
        expanded = expanded.replace("${selected_files}", " ".join(selected_files))
    expanded = expanded.replace(
        "${highlighted_file_name}", os.path.basename(highlighted)
    )
    return expanded


@lru_cache(maxsize=512)
def recache(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def command(initial_command: str, path_str: str, is_shell: bool) -> str | list[str]:
    import shlex

    if is_shell:
        return initial_command + " " + shlex.quote(path_str)
    else:
        return shlex.split(initial_command) + [path_str]
