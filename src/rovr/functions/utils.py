import os
import re
import subprocess
from contextlib import suppress
from functools import lru_cache
from typing import Any, Callable, Literal, cast, overload

from humanize import naturalsize
from textual import events
from textual.app import App, ScreenStackError
from textual.dom import DOMNode
from textual.message import Message
from textual.screen import Screen, ScreenResultType
from textual.worker import NoActiveWorker, WorkerCancelled, get_current_worker

from rovr.classes.type_aliases import ShellRunTypes
from rovr.functions.cwd import getcwd
from rovr.variables.maps import RovrVars


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
    return naturalsize(
        value=integer,
        gnu=suffix == "gnu",
        binary=suffix == "binary",
        format=f"%.{filesize_decimals}f",
    ).replace("Bytes", "B")


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
        or (
            event.is_printable
            and event.character in key_list
            # specifically check for space
            and event.character != " "
        )
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

    match least_len[1]:
        case "escape":
            least_len = (least_len[0], "esc")

    return least_len[1]


def get_shortcut(
    context: str,
    action: str,
    legacy_context: str | None = None,
    legacy_action: str | None = None,
) -> str:
    from rovr.variables.constants import config, keys

    if keys:
        binds = [
            key
            for key, binding in keys.get(context, {}).items()
            if binding["action"] == action
        ]
    else:
        legacy = cast(Any, config)["keybinds"]
        binds = legacy[legacy_context or context][legacy_action or action]
    return get_shortest_bind(binds)


def run_command(
    app: App,
    command: str | list[str],
    run_type: ShellRunTypes,
    shell: bool = True,
    on_error: Callable[[str, str], None] | None = None,
) -> subprocess.CompletedProcess | subprocess.Popen:
    if not shell and isinstance(command, str):
        from shlex import split as shplit

        command = shplit(command)
    elif shell and isinstance(command, list):
        from shlex import join as shjoin

        command = shjoin(command)
    if globals().get("is_dev", False):
        print(command)

    match run_type:
        case "orphan":
            import sys

            if sys.platform == "win32":
                return subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.DETACHED_PROCESS,
                    shell=shell,
                )
            else:
                return subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
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
    import multiprocessing

    is_dev = globals().get("is_dev", False)
    if isinstance(exc, ValueError) and "fds_to_keep" in str(exc):
        match multiprocessing.get_start_method(allow_none=True):
            case None:
                # try forkserver
                try:
                    multiprocessing.set_start_method("forkserver", force=True)
                    if is_dev:
                        app.notify("multiprocessing is now using forkserver")
                except ValueError as val_exc:
                    if "cannot find context" in str(val_exc):
                        multiprocessing.set_start_method("spawn", force=True)
                        if is_dev:
                            app.notify("multiprocessing is now using spawn")
            case "fork":  # theoretically this shouldn't happen
                multiprocessing.set_start_method("forkserver", force=True)
                if is_dev:
                    app.notify("multiprocessing is now using forkserver")
            case "forkserver":
                multiprocessing.set_start_method("spawn", force=True)
                if is_dev:
                    app.notify("multiprocessing is now using spawn")
            case "spawn":
                # nothing else we can do, except forcefully stop using Process
                app.MULTIPROCESSING_PROCESS_ALLOWED = False
        return True
    return False


percent_expand = re.compile(r"%([tT])(\d*)h(?![a-zA-Z0-9_])|%[a-zA-Z_]+")


@overload
async def expand_command(app: App, command: str) -> str: ...


@overload
async def expand_command(app: App, command: list[str]) -> list[str]: ...


async def expand_command(app: App, command: str | list[str]) -> str | list[str]:
    from shlex import join as shjoin

    from rovr.functions.path import normalise
    from rovr.header.tabs import TablineTab

    cwd = normalise(getcwd())
    highlighted = ""
    if app.file_list.highlighted_option is not None and hasattr(
        app.file_list.highlighted_option, "dir_entry"
    ):
        highlighted = normalise(app.file_list.highlighted_option.dir_entry.path)
    selected = app.query_one("Clipboard").selected
    copy, cut = (
        [item.path for item in selected if item.type_of_selection == "copy"],
        [item.path for item in selected if item.type_of_selection == "cut"],
    )

    selected_files = await app.file_list.get_selected_objects() or []
    tabs = list(app.tabWidget.query(TablineTab))

    def _expand_tab(match: re.Match[str]) -> str:
        direction, distance = match.group(1), match.group(2)
        if not tabs or app.tabWidget.active_tab not in tabs:
            return match.group(0)
        target = tabs[
            (
                tabs.index(app.tabWidget.active_tab)
                + (int(distance or 1) * (1 if direction == "t" else -1))
            )
            % len(tabs)
        ]
        if target is app.tabWidget.active_tab:
            return highlighted
        last_highlight = target.session.lastHighlighted.get(target.directory)
        name = last_highlight["name"] if last_highlight else target.focus_on
        return normalise(os.path.join(target.directory, name)) if name else ""

    def _expand(cmd: str) -> str:
        # deprecated stuff
        expanded = cmd.replace("${current_working_directory}", cwd).replace(
            "${real_current_working_directory", os.path.realpath(cwd)
        )
        expanded = expanded.replace("${highlighted_file}", highlighted).replace(
            "${real_highlighted_file}", os.path.realpath(highlighted)
        )
        expanded = expanded.replace(
            "${selected_files}", shjoin(selected_files)
        ).replace(
            "${real_selected_files}",
            shjoin([os.path.realpath(f) for f in selected_files]),
        )
        expanded = expanded.replace(
            "${highlighted_file_name}", os.path.basename(highlighted)
        ).replace(
            "${real_highlighted_file_name}",
            os.path.basename(os.path.realpath(highlighted)),
        )
        if cmd != expanded:
            app.notify(
                "Expansion syntax [primary]${thing}[/] is deprecated, please use [primary]%thing[/] instead",
                timeout=5,
                severity="warning",
            )
        # we will start using %<thing> from now on
        # scan for %<thing>
        if percent_expand.search(expanded):
            expanded = percent_expand.sub(
                # have i told you how frigtening my brain is
                lambda match: (
                    _expand_tab(match)
                    if match.group(1) is not None
                    else {
                        "%cwd": lambda: cwd,
                        "%rcwd": lambda: os.path.realpath(cwd),
                        "%ncwd": lambda: os.path.basename(cwd),
                        "%rncwd": lambda: os.path.realpath(os.path.realpath(cwd)),
                        "%h": lambda: highlighted,
                        "%rh": lambda: os.path.realpath(highlighted),
                        "%nh": lambda: os.path.basename(highlighted),
                        "%rnh": lambda: os.path.basename(os.path.realpath(highlighted)),
                        "%s": lambda: shjoin(selected_files),
                        "%rs": lambda: shjoin([
                            os.path.realpath(f) for f in selected_files
                        ]),
                        "%cut": lambda: shjoin(cut),
                        "%copy": lambda: shjoin(copy),
                    }.get(match.group(0), lambda: match.group(0))()
                ),
                expanded,
            )

        return expanded

    if isinstance(command, list):
        to_return = [_expand(cmd) for cmd in command]
    else:
        to_return = _expand(command)
    if globals().get("is_dev", False):
        print(f"{command}\n-> {to_return}")
    return to_return


@lru_cache(maxsize=512)
def recache(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def command(
    initial_command: str | list[str] | tuple[str], path_str: str
) -> str | list[str]:
    import shlex

    if isinstance(initial_command, tuple):
        initial_command = list(initial_command)
    if isinstance(initial_command, list):
        return initial_command + [path_str]
    else:
        return initial_command + " " + shlex.quote(path_str)


def s(item: Any, notone: str = "s", isone: str = "") -> str:
    return isone if len(item) == 1 else notone


preview_loc = os.path.join(RovrVars.ROVRTEMP, "previews")


def load_from_cache(
    realpath: str,
    preview_type: str,
    stat_res: os.stat_result,
    sig: tuple[str, str],
    extra: Any = None,
    pass_as: type[Any] = bytes,
) -> Any | None:
    from hashlib import blake2b

    hash = blake2b(
        f"{realpath}:{preview_type}:{stat_res.st_mtime_ns}:{stat_res.st_size}:{sig[0]}:{sig[1]}:{extra}".encode(),
        digest_size=16,
    ).hexdigest()
    cache_path = os.path.join(preview_loc, hash)
    try:
        with open(cache_path, "rb") as f:
            content = f.read()
        if pass_as is list or pass_as is dict:
            import json

            return json.loads(content.decode())
        elif pass_as is str:
            return content.decode()
        return content
    except OSError:
        pass


def save_to_cache(
    realpath: str,
    preview_type: str,
    stat_res: os.stat_result,
    sig: tuple[str, str],
    data: Any,
    extra: Any = None,
) -> None:
    from hashlib import blake2b

    hash = blake2b(
        f"{realpath}:{preview_type}:{stat_res.st_mtime_ns}:{stat_res.st_size}:{sig[0]}:{sig[1]}:{extra}".encode(),
        digest_size=16,
    ).hexdigest()
    try:
        os.makedirs(preview_loc, exist_ok=True)
        if isinstance(data, (dict, list)):
            import json

            data = json.dumps(
                data, ensure_ascii=False, check_circular=False, separators=(",", ":")
            ).encode()
        elif isinstance(data, str):
            data = data.encode()
        elif not isinstance(data, bytes):
            data = str(data).encode()
        with open(os.path.join(preview_loc, hash), "wb") as f:
            f.write(data)
    except OSError:
        pass
