from os import getcwd, path, scandir
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
        """Get the candidates for the current path segment, folders only.
        Args:
            target_state (TargetState): The current state of the Input element

        Returns:
            list[DropdownItem]: A list of DropdownItems to use as AutoComplete"""
        current_input = target_state.text[: target_state.cursor_position]

        if "/" in current_input:
            last_slash_index = current_input.rindex("/")
            path_segment = current_input[:last_slash_index] or "/"
            directory = self.path / path_segment if path_segment != "/" else self.path
        else:
            directory = self.path

        # Use the directory path as the cache key
        cache_key = str(directory)
        cached_entries = self._directory_cache.get(cache_key)

        if cached_entries is not None:
            entries = cached_entries
        else:
            try:
                entries = list(scandir(directory))
                self._directory_cache[cache_key] = entries
            except OSError:
                return []

        results: list[PathDropdownItem] = []
        has_directories = False

        for entry in entries:
            if entry.is_dir():
                has_directories = True
                completion = entry.name
                if not self.show_dotfiles and completion.startswith("."):
                    continue
                completion += "/"
                results.append(PathDropdownItem(completion, path=Path(entry.path)))

        if not has_directories:
            self._empty_directory = True
            return [DropdownItem("", prefix="No folders found")]
        else:
            self._empty_directory = False

        # this kinda is required, for some reason, ty doesn't
        # know yet that you can sort while providing a key
        results.sort(key=self.sort_key)  # ty: ignore[no-matching-overload]
        folder_prefix = self.folder_prefix
        return [
            DropdownItem(
                item.main,
                prefix=folder_prefix,
            )
            for item in results
        ]

    def _align_to_target(self) -> None:
        """Empty function that was supposed to align the completion box to the cursor."""
        pass

    def _on_show(self, event: events.Show) -> None:
        super()._on_show(event)
        self._target.add_class("hide_border_bottom", update=True)

    async def _on_hide(self, event: events.Hide) -> None:
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
            self.app.cd(event.value)
        else:
            self.notify("Path provided is not valid.", severity="error")
        self.app.query_one("#file_list").focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "backspace":
            event.stop()
            self.action_delete_left()
