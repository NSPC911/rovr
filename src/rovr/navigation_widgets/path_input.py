from os import getcwd, path
from pathlib import Path
from typing import cast

from textual import events
from textual.validation import Function
from textual.widgets import Input
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from rovr.functions.icons import get_icon


class PathDropdownItem(DropdownItem):
    def __init__(self, completion: str, path: Path) -> None:
        super().__init__(completion)
        self.path = path


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
        default_behavior = super().should_show_dropdown(search_string)
        return (
            default_behavior
            or (search_string == "" and self.target.value != "")
            and self.option_list.option_count > 0
        )

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        import string
        from pathlib import Path

        from textual.fuzzy import Matcher

        # If empty string, return available drives
        path_str = target_state.text
        if not path_str:
            drives = []
            for letter in string.ascii_uppercase:
                drive_path = Path(f"{letter}:/")
                if drive_path.exists():
                    drives.append(f"{letter}:/")
            return drives

        # Parse the input path
        path_obj = Path(path_str)

        # Handle drive letter inputs (C, C:, C:/)
        if len(path_str) <= 3 and path_str[0].isalpha():
            # Extract drive letter
            drive_letter = path_str[0].upper()
            return [DropdownItem(f"{drive_letter}:/")]

        # Determine parent directory and search pattern
        if path_str.endswith("/") or path_str.endswith("\\"):
            # List contents of this directory
            parent = path_obj
            pattern = ""
        else:
            # Check if the path exists as a directory
            if path_obj.exists() and path_obj.is_dir():
                # If it's a directory but doesn't end with /, return it with /
                return [DropdownItem(path_obj.name + "/")]

            # Otherwise, treat the last part as a search pattern
            parent = path_obj.parent
            pattern = path_obj.name

        # Get all directories in parent
        try:
            directories = []
            for item in parent.iterdir():
                if item.is_dir():
                    directories.append(item.name)

            # Apply fuzzy matching if there's a pattern
            if pattern:
                matcher = Matcher(pattern)
                matched = []
                for dir_name in directories:
                    score = matcher.match(dir_name)
                    if score > 0:
                        matched.append((score, dir_name))
                # Sort by score (descending) to get best matches first
                matched.sort(key=lambda x: x[0], reverse=True)
                return [DropdownItem(name) for _, name in matched]

            return [DropdownItem(name) for name in directories]

        except (FileNotFoundError, PermissionError):
            return []

    def _align_to_target(self) -> None:
        """Empty function that was supposed to align the completion box to the cursor."""
        pass

    def _on_show(self, event: events.Show) -> None:
        super()._on_show(event)
        self._target.add_class("hide_border_bottom", update=True)

    def _on_hide(self, event: events.Hide) -> None:
        super()._on_hide(event)
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
