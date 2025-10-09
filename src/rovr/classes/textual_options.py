from os import DirEntry

from textual.content import Content, ContentText
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection, SelectionType


class PinnedSidebarOption(Option):
    def __init__(self, icon: list, label: str, *args, **kwargs) -> None:
        super().__init__(
            prompt=Content.from_markup(
                f" [{icon[1]}]{icon[0]}[/{icon[1]}] $name", name=label
            ),
            *args,
            **kwargs,
        )
        self.label = label


class FileListSelectionWidget(Selection):
    # Cache for pre-parsed icon Content objects to avoid repeated markup parsing
    _icon_content_cache: dict[tuple[str, str], Content] = {}

    def __init__(
        self,
        icon: list[str],
        label: str,
        dir_entry: DirEntry,
        value: SelectionType,
        disabled: bool = False,
    ) -> None:
        """
        Initialise the selection.

        Args:
            icon (list[str]): The icon list from a utils function.
            label (str): The label for the option.
            dir_entry (DirEntry): The nt.DirEntry class
            value (SelectionType): The value for the selection.
            disabled (bool) = False: The initial enabled/disabled state. Enabled by default.
        """
        cache_key = (icon[0], icon[1])
        if cache_key not in FileListSelectionWidget._icon_content_cache:
            # Parse the icon markup once and cache it as Content
            FileListSelectionWidget._icon_content_cache[cache_key] = Content.from_markup(
                f" [{icon[1]}]{icon[0]}[/{icon[1]}] "
            )

        # Create prompt by combining cached icon content with label
        prompt = FileListSelectionWidget._icon_content_cache[cache_key] + Content(label)

        super().__init__(prompt=prompt, value=value, id=str(value), disabled=disabled)
        self.dir_entry = dir_entry
        self.label = label


class ClipboardSelection(Selection):
    def __init__(self, prompt: ContentText, *args, **kwargs) -> None:
        """
        Initialise the selection.

        Args:
            prompt: The prompt for the selection.
            value: The value for the selection.
            initial_state: The initial selected state of the selection.
            id: The optional ID for the selection.
            disabled: The initial enabled/disabled state. Enabled by default.
        """
        super().__init__(prompt, *args, **kwargs)
        self.initial_prompt = prompt


class KeybindOption(Option):
    def __init__(
        self,
        keys: str,
        description: str,
        max_key_width: int,
        primary_key: str,
        **kwargs,
    ) -> None:
        # Should be named 'label' for searching
        self.label = f" {keys:>{max_key_width}} │ {description} "
        self.key_press = primary_key

        super().__init__(self.label, **kwargs)
        if primary_key == "":
            self.disabled = True


class FinderOption(Option):
    # icon cache
    _icon_content_cache: dict[tuple[str, str], Content] = {}

    def __init__(
        self,
        icon: list[str],
        label: str,
        id: str = "",
        disabled: bool = False,
    ) -> None:
        """
        Initialise the option

        Args:
            icon (list[str]): The icon list from a utils function.
            label (str): The label for the option.
            id (str): The optional id for the option.
            disabled (bool) = False: The initial enabled/disabled state.
        """
        cache_key = (icon[0], icon[1])
        if cache_key not in FinderOption._icon_content_cache:
            # Parse
            FinderOption._icon_content_cache[cache_key] = Content.from_markup(
                f" [{icon[1]}]{icon[0]}[/] "
            )

        # create prompt
        prompt = FinderOption._icon_content_cache[cache_key] + Content(label)
        super().__init__(prompt=prompt, disabled=disabled, id=id)
        self.label = label
