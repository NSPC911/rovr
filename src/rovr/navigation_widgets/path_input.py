import os
import stat
import sys
from os import path
from pathlib import Path
from typing import ClassVar, Generator, cast

from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.css.query import NoMatches
from textual.validation import Function
from textual.widgets import Input
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from rovr.classes.mixins import Action, Actionable
from rovr.classes.textual_options import PathDropdownItem
from rovr.functions.cwd import getcwd
from rovr.functions.icons import get_icon
from rovr.functions.utils import check_key
from rovr.variables.constants import config


def get_subdirectories(parent: str | os.PathLike) -> Generator[os.DirEntry, None, None]:
    try:
        with os.scandir(parent) as it:
            for entry in it:
                if entry.is_dir():
                    yield entry
    except (FileNotFoundError, OSError):
        return


def is_dir_entry_hidden(entry: os.DirEntry) -> bool:
    """Check whether a ``DirEntry`` represents a hidden item.

    Args:
        entry: A ``DirEntry`` from ``os.scandir``.

    Returns:
        ``True`` if the entry is hidden, ``False`` otherwise.
    """
    if entry.name.startswith(".") and sys.platform != "win32":
        return True
    try:
        file_stat = entry.stat(follow_symlinks=False)
    except OSError:
        return False

    if sys.platform == "darwin":
        return bool(file_stat.st_flags & stat.UF_HIDDEN)
    if sys.platform == "win32":
        return bool(file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    return False


def should_exclude_hidden(path_str: str) -> bool:
    """Decide whether hidden entries must be excluded from autocomplete results.

    When the user explicitly types something that starts with ``.`` we let
    the dropdown show hidden entries so they can reach ``.config``, ``.local``,
    etc.  Otherwise hidden entries are filtered out.

    The special component ``..`` always results in filtering because it
    represents navigation rather than prefix matching.  Single ``.`` does
    **not** filter — it acts as an explicit invitation to see dotfiles.

    Args:
        path_str: The raw value inside the path input widget.

    Returns:
        ``True`` when hidden entries should be filtered, ``False`` when they
        should be listed.
    """
    # Never filter when the raw input is empty
    if not path_str:
        return False

    # Navigation tokens never reveal hidden files.
    if path_str.endswith(".."):
        return True

    if config["interface"]["show_hidden_files"]:
        return False

    # User typed something that starts with a dot -> show hidden files.
    head, tail = os.path.split(path_str)
    if not tail:
        return True
    return not tail.startswith(".")


def _unix_get_candidates(path_str: str) -> list[DropdownItem]:
    # Case 1: nothing
    if not path_str:
        return [PathDropdownItem("/", "/")]

    # Reject relative paths - must be absolute
    if not path.isabs(path_str):
        return []

    # User is going up, no need to provide autocomplete.
    if path_str.endswith(".."):
        return []

    # We treat differently for "/path/to/folder" and "/path/to/folder/",
    # but `Path.resolve` will strip the trailing "/",
    # so sometimes we have to check against the original `path_str`.
    ppath = Path(path_str).expanduser().resolve()

    # Case 2: exact directory match
    # User typed path of a particular folder already (but without the trailing "/")
    if (
        not path_str.endswith(".")
        and not path_str.endswith("/")
        and ppath.exists()
        and ppath.is_dir()
    ):
        return [PathDropdownItem(f"{ppath.name}/", str(ppath))]

    # Case 3: list contents of parent
    # - User typed a directory path with trailing "/" -> show subdirectories
    # - User typed a partial directory path (like "/home/user/.local/sh")
    #   -> we determine the parent ("~/.local") then show subdirectories ("share")
    parent = ppath if ppath.is_dir() else ppath.parent
    items: list[DropdownItem] = []
    should_filter = should_exclude_hidden(path_str)
    for entry in get_subdirectories(parent):
        if should_filter and is_dir_entry_hidden(entry):
            continue
        items.append(PathDropdownItem(f"{entry.name}/", entry.path))
    items.sort(key=lambda x: x.path.lower())
    return items


def _win_get_candidates(path_str: str) -> list[DropdownItem]:
    """Windows-specific path autocomplete using ``scandir`` and ``DirEntry``.

    Handles drive-letter discovery, bare/drive inputs (``C``, ``C:``), and
    directory traversal on Windows.  Hidden directories are filtered unless
    the terminal component starts with a dot.

    Args:
        path_str: The raw value inside the Windows path input widget.

    Returns:
        A list of ``DropdownItem`` suggestions, or an empty list when no
        candidates are available.
    """
    # Case 1: Empty string - return available drives
    if not path_str:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:/"
            if path.exists(drive):
                drives.append(PathDropdownItem(drive, drive))
        return drives

    # Case 2: Just a drive letter (e.g., "C") or drive with colon (e.g., "C:")
    if 0 < len(path_str) <= 2 and path_str[0].isalpha():
        if len(path_str) == 2 and path_str[1] != ":":
            return []  # invalid format
        drive_letter = path_str[0].upper()
        drive = f"{drive_letter}:/"
        if path.exists(drive):
            return [PathDropdownItem(drive, drive)]
        return []

    # Reject relative paths - must be absolute (has drive letter)
    if not path.isabs(path_str):
        return []

    ppath = Path(path_str).expanduser().resolve()
    if path_str.endswith(".."):
        return []

    # Case 3: exact directory match
    # User typed path of a particular folder already (but without the trailing "\")
    if (
        not path_str.endswith(".")
        and not path_str.endswith(("\\", "/"))
        and ppath.exists()
        and ppath.is_dir()
    ):
        return [PathDropdownItem(f"{ppath.name}{os.path.sep}", str(ppath))]

    # Case 4: list contents of parent
    # - Path ends with "/" -> show subdirectories
    # - Partial path like "C:\Users\Admin\Doc" -> parent is "C:\Users\Admin"
    parent = ppath if ppath.exists() else ppath.parent
    items: list[DropdownItem] = []
    should_filter = should_exclude_hidden(path_str)
    for entry in get_subdirectories(parent):
        if should_filter and is_dir_entry_hidden(entry):
            continue
        items.append(PathDropdownItem(f"{entry.name}\\", entry.path))
    items.sort(key=lambda x: x.path.lower())
    return items


class PathAutoCompleteInput(PathAutoComplete):
    def __init__(self, target: Input) -> None:
        """An autocomplete widget for filesystem paths.

        Args:
            target: The target input widget to autocomplete.
        """
        super().__init__(
            target=target,
            path=getcwd().split(path.sep)[0],
            id="path_autocomplete",
            sort_key=lambda item: item.lower(),
        )
        self.folder_prefix = " " + get_icon("folder", "default")[0] + " "
        self.file_prefix = " " + get_icon("file", "default")[0] + " "
        self._target: Input = target
        assert isinstance(self._target, Input)

    def _get_target_state(self) -> TargetState:
        return TargetState(
            text=self.target.value,
            cursor_position=len(self.target.value),
        )

    def should_show_dropdown(self, search_string: str) -> bool:
        # ignore search_string, it's inaccurate
        return self.option_list.option_count > 0 and (
            self._target.has_focus or self.has_focus
        )

    def _compute_matches(
        self, target_state: TargetState, search_string: str
    ) -> list[DropdownItem]:
        candidates = self.get_candidates(target_state)
        if not candidates:
            return []
        matches = self.get_matches(target_state, candidates, search_string)
        return matches

    def _rebuild_options(self, target_state: TargetState, search_string: str) -> None:
        """Rebuild the options in the dropdown.

        Args:
            target_state: The state of the target widget.
        """
        option_list = self.option_list
        if self.target.has_focus:
            matches = self._compute_matches(target_state, search_string)
            if matches:
                option_list.set_options(matches)
                option_list.highlighted = None
            elif matches == []:
                option_list.clear_options()
                option_list.highlighted = None

    def _listen_to_messages(self, event: events.Event) -> None:
        """Listen to some events of the target widget."""
        try:
            option_list = self.option_list
        except NoMatches:
            # This can happen if the event is an Unmount event
            # during application shutdown.
            event.prevent_default()
            return

        if isinstance(event, events.Key) and option_list.option_count:
            displayed = self.display
            match event.key:
                case "down":
                    if option_list.highlighted is None:
                        option_list.highlighted = 0
                        event.prevent_default()
                        return
                    elif option_list.highlighted == option_list.option_count - 1:
                        option_list.set_reactive(type(option_list).highlighted, 0)
                        option_list.scroll_to_highlight()
                        option_list.set_reactive(type(option_list).highlighted, None)
                        event.prevent_default()
                        return
                    # Check if there's only one item and it matches the search string
                    if option_list.option_count == 1:
                        search_string = self.get_search_string(self._get_target_state())
                        first_option = option_list.get_option_at_index(0).prompt
                        text_from_option = (
                            first_option.plain
                            if isinstance(first_option, Text)
                            else first_option
                        )
                        if text_from_option == search_string:
                            event.prevent_default()
                            return

                    # If you press `down` while in an Input and the autocomplete is currently
                    # hidden, then we should show the dropdown.
                    event.prevent_default()
                    event.stop()
                    if displayed:
                        option_list.highlighted = (
                            option_list.highlighted + 1
                        ) % option_list.option_count
                    else:
                        self.display = True
                        option_list.highlighted = 0

                    option_list.highlighted = option_list.highlighted
                case "up":
                    if displayed:
                        event.prevent_default()
                        event.stop()
                        if option_list.highlighted == 0:
                            option_list.highlighted = None
                            return
                        if option_list.highlighted is None:
                            option_list.highlighted = len(option_list.options) - 1
                            return
                        option_list.highlighted = (
                            option_list.highlighted - 1
                        ) % option_list.option_count
                        option_list.highlighted = option_list.highlighted
                case "enter":
                    if option_list.highlighted is None:
                        return
                    if displayed:
                        event.prevent_default()
                        event.stop()
                    if option_list.highlighted is not None:
                        self._complete(option_list.highlighted)
                case "tab":
                    if displayed:
                        event.prevent_default()
                        event.stop()
                    if (
                        option_list.highlighted is None
                        and option_list.option_count != 1
                    ):
                        option_list.highlighted = 0
                    else:
                        highlighted: int = option_list.highlighted or 0
                        self._complete(highlighted)
                case "escape":
                    event.prevent_default()
                    event.stop()
                    self.action_hide()
                case _:
                    return
            event.prevent_default()
        else:
            super()._listen_to_messages(event)

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        if sys.platform == "win32":
            return _win_get_candidates(target_state.text)
        return _unix_get_candidates(target_state.text)

    def _align_to_target(self) -> None:
        """Empty function that was supposed to align the completion box to the cursor."""
        pass

    def _on_show(self, event: events.Show) -> None:
        self._target.add_class("hide_border_bottom", update=True)

    def _on_hide(self, event: events.Hide) -> None:
        event.prevent_default()
        if self.show_horizontal_scrollbar:
            self.horizontal_scrollbar.post_message(event)
        if self.show_vertical_scrollbar:
            self.vertical_scrollbar.post_message(event)
        self._target.remove_class("hide_border_bottom", update=True)

    def _complete(self, option_index: int) -> None:
        """Do the completion (i.e. insert the selected item into the target input).

        This is when the user highlights an option in the dropdown and presses tab or enter.
        """
        if not self.display or self.option_list.option_count == 0:
            return

        option_list = self.option_list
        highlighted = option_index
        option = cast(DropdownItem, option_list.get_option_at_index(highlighted))
        highlighted_value = option.value
        if highlighted_value == "":
            # nothing there
            self.action_hide()
            self._target.post_message(
                Input.Submitted(self._target, self._target.value, None)
            )
            return
        with self.prevent(Input.Changed):
            self.apply_completion(highlighted_value, self._get_target_state())
        self.post_completion()


class PathInput(Actionable, Input, inherit_bindings=False):
    ALLOW_MAXIMIZE = False
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "cursor_left", "Move cursor left", show=False),
        Binding(
            "shift+left",
            "cursor_left(True)",
            "Move cursor left and select",
            show=False,
        ),
        Binding("ctrl+left", "cursor_left_word", "Move cursor left a word", show=False),
        Binding(
            "ctrl+shift+left",
            "cursor_left_word(True)",
            "Move cursor left a word and select",
            show=False,
        ),
        Binding(
            "right",
            "cursor_right",
            "Move cursor right or accept the completion suggestion",
            show=False,
        ),
        Binding(
            "shift+right",
            "cursor_right(True)",
            "Move cursor right and select",
            show=False,
        ),
        Binding(
            "ctrl+right",
            "cursor_right_word",
            "Move cursor right a word",
            show=False,
        ),
        Binding(
            "ctrl+shift+right",
            "cursor_right_word(True)",
            "Move cursor right a word and select",
            show=False,
        ),
        Binding("delete,ctrl+d", "delete_right", "Delete character right", show=False),
        Binding("enter", "submit", "Submit", show=False),
        Binding(
            "ctrl+w", "delete_left_word", "Delete left to start of word", show=False
        ),
        Binding("ctrl+u", "delete_left_all", "Delete all to the left", show=False),
        Binding(
            "ctrl+f", "delete_right_word", "Delete right to start of word", show=False
        ),
        Binding("ctrl+k", "delete_right_all", "Delete all to the right", show=False),
        Binding("ctrl+x", "cut", "Cut selected text", show=False),
        Binding("ctrl+c,super+c", "copy", "Copy selected text", show=False),
        Binding("ctrl+v", "paste", "Paste text from the clipboard", show=False),
    ]

    def __init__(self) -> None:
        super().__init__(
            id="path_switcher",
            validators=[
                Function(lambda x: path.isabs(x), "Path must be absolute"),
                Function(lambda x: path.exists(x), "Path does not exist"),
            ],
            validate_on=["changed"],
            select_on_focus=False,
        )
        self.ACTIONS: list[Action] = [
            Action(self.action_delete_left, "backspace"),
            Action(self.app.file_list.focus, "escape"),
        ]

    def on_mount(self) -> None:
        self.auto_completer = self.app.query_one(PathAutoCompleteInput)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Use a custom path entered as the current working directory"""
        if not path.isabs(event.value):
            self.notify("Path must be absolute.", severity="error")
        elif path.exists(event.value) and event.value != "":
            self.app.cd(event.value, clear_search=True)
        else:
            self.notify("Path provided is not valid.", severity="error")
        self.app.file_list.focus()

    async def on_key(self, event: events.Key) -> None:
        if len(event.key) != 1 and not event.is_printable:
            if check_key(event, config["keybinds"]["toggle_all"]):
                self.select_all()
            elif check_key(event, config["keybinds"]["home"]):
                self.action_home()
            elif check_key(event, config["keybinds"]["end"]):
                self.action_end()
            elif check_key(event, config["keybinds"]["select_home"]):
                self.action_home(select=True)
            elif check_key(event, config["keybinds"]["select_end"]):
                self.action_end(select=True)
            else:
                return
        else:
            return

    def on_blur(self) -> None:
        self.auto_completer.action_hide()

    def on_focus(self) -> None:
        self.app.call_after_refresh(
            self.auto_completer._listen_to_messages, Input.Changed(self, self.value)
        )
