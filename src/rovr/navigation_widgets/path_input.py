from os import getcwd, path, scandir
from pathlib import Path

from textual import events
from textual.validation import Function
from textual.widgets import Input
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from rovr.utils import get_icon


class PathDropdownItem(DropdownItem):
    def __init__(self, completion: str, path: Path) -> None:
        super().__init__(completion)
        self.path = path


class PathAutoCompleteInput(PathAutoComplete):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            path=getcwd().split(path.sep)[0],
            folder_prefix=" " + get_icon("folder", "default")[0] + " ",
            file_prefix=" " + get_icon("file", "default")[0] + " ",
            id="path_autocomplete",
            *args,
            **kwargs,
        )

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

        results.sort(key=self.sort_key)
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
        await self._target.action_submit()
        self._target.focus()


class PathInput(Input):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            id="path_switcher",
            validators=[Function(lambda x: path.exists(x), "Path does not exist")],
            validate_on=["changed"],
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Use a custom path entered as the current working directory"""
        self.app.cd(event.value)

    def on_key(self, event: events.Key) -> None:
        if event.key == "backspace":
            event.stop()
            self.action_delete_left()
