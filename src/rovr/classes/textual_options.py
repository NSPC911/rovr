from os import DirEntry

from textual.content import Content, ContentText
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection


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
    def __init__(
        self, icon: list, label: str, dir_entry: DirEntry, *args, **kwargs
    ) -> None:
        """
        Initialise the selection.

        Args:
            icon (list): The icon list from a utils function.
            label (str): The label for the option.
            dir_entry (DirEntry): The nt.DirEntry class
            value (SelectionType): The value for the selection.
            initial_state (bool) = False: The initial selected state of the selection.
            id (str or None) = None: The optional ID for the selection.
            disabled (bool) = False: The initial enabled/disabled state. Enabled by default.
        """
        super().__init__(
            prompt=Content.from_markup(
                f" [{icon[1]}]{icon[0]}[/{icon[1]}] $name", name=label
            ),
            *args,
            **kwargs,
        )
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
