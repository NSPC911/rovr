import os
import re
import subprocess
from contextlib import AbstractContextManager, contextmanager, suppress
from typing import (
    Any,
    Callable,
    Literal,
    TypeVar,
    cast,
    overload,
)

from humanize import naturalsize
from textual import events
from textual.app import App, ScreenStackError
from textual.dom import DOMNode
from textual.message import Message
from textual.screen import Screen, ScreenResultType
from textual.worker import NoActiveWorker, WorkerCancelled, get_current_worker

from rovr.classes.type_aliases import CallableNone, ShellRunTypes
from rovr.functions.cwd import getcwd


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
    # return exc.errno == errno.EACCES


def should_cancel() -> bool:
    """
    Whether the current worker should cancel execution

    Returns:
        bool: whether to cancel this worker or not
    """
    try:
        worker = get_current_worker()
    except (NoActiveWorker, RuntimeError):
        return False
    except WorkerCancelled:
        return True
    return bool(worker and not worker.is_running)


class ExitNow(RuntimeError): ...


def check_cancel(do_raise: bool = True) -> bool:
    if should_cancel():
        if do_raise:
            raise ExitNow()
        return True
    return False


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


def get_shortcut(
    context: str,
    action: str,
    legacy_context: str | None = None,
    legacy_action: str | None = None,
) -> str:
    from rovr.variables.constants import config, keys

    if keys:

        def find_bindings(
            bindings: dict[str, Any], prefix: tuple[str, ...] = ()
        ) -> list[tuple[str, ...]]:
            matches = []
            for key, binding in bindings.items():
                if not isinstance(binding, dict):
                    continue
                sequence = prefix + (key,)
                if binding.get("action") == action:
                    matches.append(sequence)
                elif "action" not in binding:
                    matches.extend(find_bindings(binding, sequence))
            return matches

        binds = [
            sequence[0]
            if len(sequence) == 1
            else "".join(f"<{key}>" if "+" in key else key for key in sequence)
            for sequence in find_bindings(keys.get(context, {}))
        ]
    else:
        legacy = cast(Any, config)["keybinds"]
        binds = legacy[legacy_context or context][legacy_action or action]

    # get_shortest_bind
    least_len: tuple[int | None, str] = (None, "")
    for bind in binds:
        if least_len[0] is None or least_len[0] > len(bind):
            least_len = (len(bind), bind)

    match least_len[1]:
        case "escape":
            least_len = (least_len[0], "esc")

    return least_len[1]


def run_command(
    app: App,
    command: str | list[str],
    run_type: ShellRunTypes,
    shell: bool = True,
    on_error: Callable[[str, str], None] | None = None,
) -> subprocess.CompletedProcess | subprocess.Popen:
    if not shell and isinstance(command, str):
        from oslex import split as shplit

        command = shplit(command)
    elif shell and isinstance(command, list):
        from oslex import join as shjoin

        command = shjoin(command)
    if "devtools" in app.features:
        app.log(command)

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
                    try:
                        return subprocess.run(command, shell=shell)
                    except Exception as e:
                        exc = e
                raise exc

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


async def expand_command(
    app: App, command: str | list[str], banned_exp: list[str] = []
) -> str | list[str]:
    from oslex import join as shjoin

    from rovr.functions.path import normalise
    from rovr.header.tabs import TablineTab

    cwd = normalise(getcwd())
    highlighted = ""
    if app.file_list.highlighted_option is not None and hasattr(
        app.file_list.highlighted_option, "dir_entry"
    ):
        highlighted = normalise(app.file_list.highlighted_option.dir_entry.path)
    selected: tuple[Literal["copy", "cut"] | None, list[str]] = app.query_one(
        "Clipboard"
    ).selected
    clipboard_type, clipboard_files = selected
    if clipboard_type is None:
        clipboard_files = []

    commands = [command] if isinstance(command, str) else command
    selected_files = (
        (await app.file_list.get_selected_objects() or [])
        # get it only if the command actually needs it, it is slightly expensive
        if any(
            token in cmd
            for cmd in commands
            for token in ("${selected_files}", "${real_selected_files}", "%s", "%rs")
        )
        else []
    )
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
        expanded = (
            cmd
            .replace("${current_working_directory}", cwd)
            .replace("${highlighted_file}", highlighted)
            .replace("${selected_files}", shjoin(selected_files))
            .replace("${highlighted_file_name}", os.path.basename(highlighted))
        )
        # real is really expensive, so expand only when necessary
        if "${real_current_working_directory" in expanded:
            expanded = expanded.replace(
                "${real_current_working_directory", os.path.realpath(cwd)
            )
        if "${real_highlighted_file}" in expanded:
            expanded = expanded.replace(
                "${real_highlighted_file}", os.path.realpath(highlighted)
            )
        if "${real_selected_files}" in expanded:
            expanded = expanded.replace(
                "${real_selected_files}",
                shjoin([os.path.realpath(f) for f in selected_files]),
            )
        if "${real_highlighted_file_name}" in expanded:
            expanded = expanded.replace(
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
                    if match.group(1) is not None and "%tab" not in banned_exp
                    else (
                        {
                            "%cwd": lambda: cwd,
                            "%rcwd": lambda: os.path.realpath(cwd),
                            "%ncwd": lambda: os.path.basename(cwd),
                            "%rncwd": lambda: os.path.realpath(os.path.realpath(cwd)),
                            "%h": lambda: highlighted,
                            "%rh": lambda: os.path.realpath(highlighted),
                            "%nh": lambda: os.path.basename(highlighted),
                            "%rnh": lambda: os.path.basename(
                                os.path.realpath(highlighted)
                            ),
                            "%s": lambda: shjoin(selected_files),
                            "%rs": lambda: shjoin([
                                os.path.realpath(f) for f in selected_files
                            ]),
                            "%clip": lambda: shjoin(clipboard_files),
                        }.get(exp, lambda: exp)()
                        if (exp := match.group(0)) not in banned_exp
                        else exp
                    )
                ),
                expanded,
            )

        return expanded

    if isinstance(command, list):
        to_return = []
        for cmd in command:
            if cmd == "%s" and "%s" not in banned_exp:
                to_return.extend(selected_files)
            elif cmd == "%rs" and "%rs" not in banned_exp:
                to_return.extend(os.path.realpath(f) for f in selected_files)
            elif cmd == "%clip" and "%clip" not in banned_exp:
                to_return.extend(clipboard_files)
            else:
                to_return.append(_expand(cmd))
    else:
        to_return = _expand(command)
    app.log(f"{command}\n-> {to_return}")
    return to_return


def command(
    initial_command: str | list[str] | tuple[str], path_str: str
) -> str | list[str]:
    import oslex

    if isinstance(initial_command, tuple):
        initial_command = list(initial_command)
    if isinstance(initial_command, list):
        return initial_command + [path_str]
    else:
        return initial_command + " " + oslex.quote(path_str)


def s(item: Any, notone: str = "s", isone: str = "") -> str:
    return (
        isone
        if (isinstance(item, list) and len(item) == 1)
        or (type(item) is int and item == 1)
        else notone
    )


R = TypeVar("R")


def enter(obj: AbstractContextManager[R]) -> tuple[R, CallableNone]:
    resource = obj.__enter__()

    def closer() -> None:
        obj.__exit__(None, None, None)

    return resource, closer


type ErrorCallable = Callable[[BaseException], Any]


@contextmanager
def dump_on_exc(
    widget: DOMNode | None,
    *filter: type[BaseException],
    other_callers: list[ErrorCallable] | ErrorCallable | None = None,
) -> Any:
    if other_callers is not None:
        if not isinstance(other_callers, list):
            other_callers = [other_callers]
    else:
        other_callers = []
    try:
        yield
    except filter or (BaseException,) as exc:
        from rovr.functions.path import dump_exc

        dump_exc(widget, exc)
        for caller in other_callers:
            caller(exc)


def strftime(timestamp: float, format: str = "") -> str:
    from datetime import datetime

    from rovr.variables.constants import config

    return datetime.fromtimestamp(timestamp).strftime(
        format or config["metadata"]["datetime_format"]
    )
