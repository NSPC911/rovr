from os import DirEntry
from typing import Literal, NamedTuple

from textual.content import Content, ContentText
from textual.widgets import SelectionList
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection

from rovr.functions.path import normalise


class PinnedSidebarOption(Option):
    def __init__(self, icon: list, label: str, id: str | None = None) -> None:
        """Initialise the option.

        Args:
            icon: The icon for the option
            label: The text for the option
            id: An option ID for the option.
        """
        super().__init__(
            prompt=Content.from_markup(
                f" [{icon[1]}]{icon[0]}[/{icon[1]}] $name", name=label
            ),
            id=id,
        )
        self.label = label


class ArchiveFileListSelection(Selection):
    # Cache for pre-parsed icon Content objects to avoid repeated markup parsing
    _icon_content_cache: dict[tuple[str, str], Content] = {}

    def __init__(self, icon: list, label: str) -> None:
        """Initialise the option.

        Args:
            icon: The icon for the option
            label: The text for the option
        """
        cache_key = (icon[0], icon[1])
        if cache_key not in ArchiveFileListSelection._icon_content_cache:
            # Parse the icon markup once and cache it as Content
            ArchiveFileListSelection._icon_content_cache[cache_key] = (
                Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
            )

        # Create prompt by combining cached icon content with label
        prompt = ArchiveFileListSelection._icon_content_cache[cache_key] + Content(
            label
        )

        super().__init__(prompt=prompt, value="", disabled=True)
        self.label = label


class FileListSelectionWidget(Selection):
    # Cache for pre-parsed icon Content objects to avoid repeated markup parsing
    _icon_content_cache: dict[tuple[str, str], Content] = {}

    def __init__(
        self,
        icon: list[str],
        label: str,
        dir_entry: DirEntry,
        clipboard: SelectionList,
        disabled: bool = False,
    ) -> None:
        """
        Initialise the selection.

        Args:
            icon (list[str]): The icon list from a utils function.
            label (str): The label for the option.
            dir_entry (DirEntry): The nt.DirEntry class
            disabled (bool) = False: The initial enabled/disabled state. Enabled by default.
        """
        cache_key = (icon[0], icon[1])
        if cache_key not in FileListSelectionWidget._icon_content_cache:
            # Parse the icon markup once and cache it as Content
            FileListSelectionWidget._icon_content_cache[cache_key] = (
                Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
            )

        # Create prompt by combining cached icon content with label
        prompt = FileListSelectionWidget._icon_content_cache[cache_key] + Content(label)
        dir_entry_path = normalise(dir_entry.path)
        if any(
            dir_entry_path == clipboard_val.path for clipboard_val in clipboard.selected
        ):
            prompt = prompt.stylize("dim")
        self.dir_entry = dir_entry
        this_id = str(id(self))

        super().__init__(
            prompt=prompt,
            # this is kinda required for FileList.get_selected_object's select mode
            # because it gets selected (which is dictionary of values)
            # which it then queries for `id` (because there's no way to query for
            # values directly)
            value=str(this_id),
            id=str(this_id),
            disabled=disabled,
        )
        self._prompt: Content
        self.label = label

    @property
    def prompt(self) -> Content:
        return self._prompt


class ClipboardSelectionValue(NamedTuple):
    path: str
    type_of_selection: Literal["copy", "cut"]


class ClipboardSelection(Selection):
    def __init__(
        self,
        prompt: ContentText,
        text: str,
        type_of_selection: Literal["copy", "cut"],
    ) -> None:
        """
        Initialise the selection.

        Args:
            prompt: The prompt for the selection.
            text: The value for the selection.
            type_of_selection: The type of selection ("cut" or "copy")

        Raises:
            ValueError:
        """

        if type_of_selection not in ["copy", "cut"]:
            raise ValueError(
                f"type_of_selection must be either 'copy' or 'cut' and not {type_of_selection}"
            )
        super().__init__(
            prompt=prompt,
            value=ClipboardSelectionValue(text, type_of_selection),
            # in the future, if we want persistent clipboard,
            # we will have to switch to use path.compress
            id=str(id(self)),
        )
        self.initial_prompt = prompt

    @property
    def value(self) -> ClipboardSelectionValue:
        """The value for this selection."""
        return self._value


class KeybindOption(Option):
    def __init__(
        self,
        keys: str,
        description: str,
        max_key_width: int,
        primary_key: str,
        is_layer: bool,
        **kwargs,
    ) -> None:
        # Should be named 'label' for searching
        if keys == "--section--":
            self.label = f" {' ' * max_key_width} ├ {description}"
            label = f"[$accent]{self.label}[/]"
        elif description == "--section--":
            self.label = f" {keys:>{max_key_width}} ┤"
            label = f"[$primary]{self.label}[/]"
        elif keys == "<disabled>":
            self.label = f" {keys:>{max_key_width}} │ {description} "
            label = f"[$background-lighten-3]{self.label}[/]"
        else:
            self.label = f" {keys:>{max_key_width}} │ {description} "
            label = self.label
        self.key_press = primary_key

        super().__init__(label, **kwargs)
        if description == "--section--":
            self.disabled = True

        self.is_layer_bind = is_layer


class ModalSearcherOption(Option):
    # icon cache
    _icon_content_cache: dict[tuple[str, str], Content] = {}

    def __init__(
        self,
        icon: list[str] | None,
        label: str,
        file_path: str | None = None,
        disabled: bool = False,
    ) -> None:
        """
        Initialise the option

        Args:
            icon (list[str] | None): The icon list from a utils function.
            label (str): The label for the option.
            file_path (str | None): The file path
            disabled (bool) = False: The initial enabled/disabled state.
        """
        if icon:
            cache_key = (icon[0], icon[1])
            if cache_key not in ModalSearcherOption._icon_content_cache:
                # Parse
                ModalSearcherOption._icon_content_cache[cache_key] = (
                    Content.from_markup(f" [{icon[1]}]{icon[0]}[/] ")
                )

            # create prompt
            prompt = ModalSearcherOption._icon_content_cache[
                cache_key
            ] + Content.from_markup(label)
        else:
            prompt = Content(label)
        super().__init__(prompt=prompt, disabled=disabled)
        self.label = label
        self.file_path = file_path
