from os import getcwd, listdir, path
from typing import cast

from rich.text import Text
from textual import events
from textual.content import Content
from textual.css.query import NoMatches
from textual.validation import Function
from textual.widgets import Input
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.functions.icons import get_icon, get_icon_for_folder
from rovr.variables.constants import os_type


class PathDropdownItem(DropdownItem):
    def __init__(self, completion: str, path: str) -> None:
        icon = get_icon_for_folder(path)
        cache_key = (icon[0], icon[1])
        if cache_key not in FileListSelectionWidget._icon_content_cache:
            # Parse the icon markup once and cache it as Content
            FileListSelectionWidget._icon_content_cache[cache_key] = (
                Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
            )
        prefix = FileListSelectionWidget._icon_content_cache[cache_key]
        super().__init__(completion, prefix)
        self.path = path


def _unix_get_candidates(path_str: str) -> list[DropdownItem]:
    from os import listdir, path

    # Case 1: nothing
    if not path_str:
        return [PathDropdownItem("/", "/")]

    # Reject relative paths that don't start with ../ or ./
    # Allow absolute paths (start with /) and relative paths that start with .. or .
    if (
        not path_str.startswith("/")
        and not path_str.startswith(("../", "./"))
        and path_str.startswith(".")
        and path_str not in (".", "..")
    ):
        # Don't continue with dotfile/folder paths unless they start with ../ or ./
        return []

    # Case 2: exact directory match (but not if it ends with /. or /..)
    if (
        (not path_str.endswith(("/", "/.", "/..")))
        and path.exists(path_str)
        and path.isdir(path_str)
    ):
        target = path.realpath(path.expanduser(path_str))
        return [PathDropdownItem(path.basename(target) + "/", target)]

    # Case 3: list contents of parent
    parent = path.dirname(path_str)
    if path.exists(parent) and path.isdir(parent):
        items = []
        for item in listdir(parent):
            full_item_path = path.join(parent, item)
            if path.isdir(full_item_path):
                items.append(PathDropdownItem(item + "/", full_item_path))
        items.sort(key=lambda x: x.path.lower())
        return items
    return []


def _win_get_candidates(path_str: str) -> list[DropdownItem]:
    # Case 1: Empty string - return available drives
    if not path_str:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:/"
            if path.exists(drive):
                drives.append(PathDropdownItem(drive, drive))
        return drives

    # Case 2: Just a drive letter (e.g., "C") or drive with colon (e.g., "C:")
    if len(path_str) <= 2 and path_str[0].isalpha():
        drive_letter = path_str[0].upper()
        drive = f"{drive_letter}:/"
        if path.exists(drive):
            return [PathDropdownItem(drive, drive)]
        return []

    # Reject relative paths that don't start with ..\ or ../ or .\ or ./
    # Allow absolute paths (start with drive letter or /) and relative paths that start with .. or .
    is_absolute = (len(path_str) >= 2 and path_str[1] == ":") or path_str.startswith(("/", "\\"))
    if (
        not is_absolute
        and not path_str.startswith(("../", ".\\", "..\\", "./"))
        and path_str.startswith(".")
        and path_str not in (".", "..")
    ):
        # Don't continue with dotfile/folder paths unless they start with ../ or ./
        return []

    # Case 3: Check if it's an exact directory match
    # Skip this case if the path ends with /. or /.. or \. or \.. to allow listing contents
    if (
        (not path_str.endswith(("/", "\\", "/.", "/..", "\\.", "\\..")))
        and path.exists(path_str)
        and path.isdir(path_str)
    ):
        target = path.realpath(path_str)
        return [PathDropdownItem(path.basename(target) + "/", target)]

    parent = path.dirname(path_str)
    if path.exists(parent) and path.isdir(parent):
        # Case 4: Path ends with "/" - list contents of that directory (directories only)
        items = []
        for item in listdir(parent):
            full_item_path = path.join(parent, item)
            if path.isdir(full_item_path):
                items.append(PathDropdownItem(item + "/", full_item_path))
        items.sort(key=lambda x: x.path.lower())
        return items
    return []


def path_input_sort_key(item: PathDropdownItem) -> tuple[bool, bool, str]:
    """Sort key function for results within the dropdown.

    Args:
        item: The PathDropdownItem to get a sort key for.

    Returns:
        A tuple of (is_file, is_non_dotfile, lowercase_name) for sorting.
        Directories sort before files, non-dotfiles before dotfiles, then alphabetically.
    """
    name = item.path.name
    is_dotfile = name.startswith(".")
    try:
        return (not item.path.is_dir(), not is_dotfile, name.lower())
    except OSError:
        # assume it is a file
        return (True, not is_dotfile, name.lower())


class PathAutoCompleteInput(PathAutoComplete):
    def __init__(self, target: Input) -> None:
        """An autocomplete widget for filesystem paths.

        Args:
            target: The target input widget to autocomplete.
        """
        super().__init__(
            target=target,
            path=getcwd().split(path.sep)[0],
            folder_prefix=" " + get_icon("folder", "default")[0] + " ",
            file_prefix=" " + get_icon("file", "default")[0] + " ",
            id="path_autocomplete",
            sort_key=path_input_sort_key,  # ty: ignore[invalid-argument-type]
        )
        self._target: Input = target
        assert isinstance(self._target, Input)

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
        event.prevent_default()

        try:
            option_list = self.option_list
        except NoMatches:
            # This can happen if the event is an Unmount event
            # during application shutdown.
            return

        if isinstance(event, events.Key) and option_list.option_count:
            displayed = self.display
            match event.key:
                case "down":
                    if option_list.highlighted is None:
                        option_list.highlighted = 0
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
                            # Don't prevent default behavior in this case
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
                    if self.prevent_default_enter and displayed:
                        event.prevent_default()
                        event.stop()
                    if option_list.highlighted is not None:
                        self._complete(option_index=option_list.highlighted)
                case "tab":
                    if self.prevent_default_tab and displayed:
                        event.prevent_default()
                        event.stop()
                    if option_list.highlighted is None:
                        option_list.highlighted = 0
                    else:
                        self._complete(option_index=option_list.highlighted)
                case "escape":
                    if displayed:
                        event.prevent_default()
                        event.stop()
                    self.action_hide()

        if isinstance(event, Input.Changed):
            # We suppress Changed events from the target widget, so that we don't
            # handle change events as a result of performing a completion.
            self._handle_target_update()

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        if os_type == "Windows":
            return _win_get_candidates(target_state.text)
        return _unix_get_candidates(target_state.text)

    def _align_to_target(self) -> None:
        """Empty function that was supposed to align the completion box to the cursor."""
        pass

    def _on_show(self, event: events.Show) -> None:
        super()._on_show(event)
        self._target.add_class("hide_border_bottom", update=True)

    def _on_hide(self, event: events.Hide) -> None:
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


class PathInput(Input):
    ALLOW_MAXIMIZE = False

    def __init__(self) -> None:
        super().__init__(
            id="path_switcher",
            validators=[Function(lambda x: path.exists(x), "Path does not exist")],
            validate_on=["changed"],
        )

    def on_mount(self) -> None:
        self.auto_completer = self.parent.parent.query_one(PathAutoCompleteInput)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Use a custom path entered as the current working directory"""
        if path.exists(event.value) and event.value != "":
            self.app.cd(event.value, clear_search=True)
        else:
            self.notify("Path provided is not valid.", severity="error")
        self.app.file_list.focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "backspace":
            # might be used for back history, so force the behaviour
            event.stop()
            self.action_delete_left()

    def on_blur(self) -> None:
        self.auto_completer.action_hide()
