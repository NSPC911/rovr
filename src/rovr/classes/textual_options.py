from __future__ import annotations

from os import DirEntry, getcwd, path
from typing import Callable, Literal, NamedTuple, TypeAlias

import rich.repr
from textual.content import Content, ContentText
from textual.visual import Visual, VisualType
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection, SelectionType
from textual_autocomplete import DropdownItem

from rovr.functions import icons as icon_utils
from rovr.functions.path import normalise
from rovr.widgets import SelectionList

_icon_content_cache: dict[tuple[str, str], Content] = {}
IconFactory: TypeAlias = Callable[[], tuple[str, str]]


def _get_cached_icon(icon: tuple[str, str]) -> Content:
    if icon not in _icon_content_cache:
        _icon_content_cache[icon] = Content.from_markup(
            f" [{icon[1]}]{icon[0]}[/{icon[1]}] "
        )
    return _icon_content_cache[icon]


@rich.repr.auto
class LazyOption(Option):
    """Lazier version of option that only renders the prompt when necessary,
    letting the dev provide a function that generates the prompt so that
    it is lazy loaded and provided when necessary + also caches the output
    so that it doesn't have to be re-rendered every time."""

    def __init__(
        self,
        prompt: Callable[[], VisualType],
        id: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialise the option.

        Args:
            prompt: The prompt (text displayed) for the option.
            id: An option ID for the option.
            disabled: Disable the option (will be shown grayed out, and will not be selectable).

        """
        self.__prompt_factory: Callable[[], VisualType] = prompt
        self._prompt: VisualType | None = None
        self._visual: Visual | None = None
        self._id = id
        self.disabled = disabled
        self._divider = False

    @property
    def prompt(self) -> VisualType:
        """The original prompt.

        Returns:
            VisualType: The rendered prompt.
        """
        if self._prompt is None:
            self._prompt = self.__prompt_factory()
        return self._prompt

    @property
    def id(self) -> str | None:
        """Optional ID for the option."""
        return self._id

    def _set_prompt(self, prompt: VisualType) -> None:
        """Update the prompt.

        Args:
            prompt: New prompt.

        """
        self.__prompt_factory = lambda: prompt
        self._prompt = prompt
        self._visual = None

    def _invalidate_prompt_cache(self) -> None:
        """Clear cached prompt and visual so prompt factories rerun lazily."""
        self._prompt = None
        self._visual = None

    def __hash__(self) -> int:
        return id(self)

    def __rich_repr__(self) -> rich.repr.Result:
        yield "is_cached", self._prompt is not None, False
        yield "id", self._id, None
        yield "disabled", self.disabled, False
        yield "_divider", self._divider, False


class LazySelection(LazyOption, Selection[SelectionType]):
    """Lazy version of Selection that inherits from LazyOption, so it has all the lazy loading and caching features, but also has a value associated with it like Selection does."""

    def __init__(
        self,
        prompt: Callable[[], VisualType],
        value: SelectionType,
        initial_state: bool = False,
        id: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialise the selection.

        Args:
            prompt: The prompt (text displayed) for the selection.
            value: The value associated with the selection.
            initial_state: The initial selected state of the selection. Defaults to False.
            id: An option ID for the selection.
            disabled: Disable the selection (will be shown grayed out, and will not be selectable).

        """
        super().__init__(prompt, id=id, disabled=disabled)
        self._value: SelectionType = value
        self._initial_state: bool = initial_state

    @property
    def value(self) -> SelectionType:
        """The value associated with the selection."""
        return self._value

    @property
    def initial_state(self) -> bool:
        """The initial selected state of the selection."""
        return self._initial_state


class PinnedSidebarOption(Option):
    def __init__(
        self, icon: tuple[str, str], label: str, id: str | None = None
    ) -> None:
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


class ArchiveFileListSelection(LazySelection):
    def __init__(self, icon_factory: IconFactory, label: str) -> None:
        """Initialise the option.

        Args:
            icon_factory: The icon for the option
            label: The text for the option
        """

        def get_prompt() -> Content:
            return _get_cached_icon(icon_factory()) + Content(label)

        super().__init__(prompt=get_prompt, value="", disabled=True)
        self.label = label


class FileListSelectionWidget(LazySelection):
    def __init__(
        self,
        icon_factory: IconFactory,
        label: str,
        dir_entry: DirEntry,
        clipboard: SelectionList,
        disabled: bool = False,
    ) -> None:
        """
        Initialise the selection.

        Args:
            icon_factory: The icon list from a utils function or a lazy icon resolver.
            label: The label for the option.
            dir_entry: The nt.DirEntry class
            disabled: The initial enabled/disabled state. Enabled by default.
        """
        self.dir_entry = dir_entry
        this_id = str(id(self))
        self.__icon_factory = icon_factory
        self.__label = label
        self.__clipboard = clipboard

        super().__init__(
            prompt=self.get_prompt,
            # this is kinda required for FileList.get_selected_object's select mode
            # because it gets selected (which is dictionary of values)
            # which it then queries for `id` (because there's no way to query for
            # values directly)
            value=this_id,
            id=this_id,
            disabled=disabled,
        )
        self.label = label

    def get_prompt(self) -> Content:
        prompt = _get_cached_icon(self.__icon_factory()) + Content(self.__label)
        if any(
            clipboard_val.type_of_selection == "cut"
            and normalise(self.dir_entry.path) == clipboard_val.path
            for clipboard_val in self.__clipboard.selected
        ):
            return prompt.stylize("dim")
        return prompt

    @property
    def icon(self) -> tuple[str, str]:
        return self.__icon_factory()

    def set_icon(self, new_icon: tuple[str, str]) -> None:
        self.__icon_factory = lambda: new_icon
        self._invalidate_prompt_cache()


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
        self.pseudo_disabled = keys == "--section--"

        self.is_layer_bind = is_layer


class ModalSearcherOption(LazyOption):
    def __init__(
        self,
        icon_factory: IconFactory | None,
        label: str,
        file_path: str | None = None,
        disabled: bool = False,
    ) -> None:
        """
        Initialise the option

        Args:
            icon_factory (IconFactor | None): The icon list from a utils function.
            label (str): The label for the option.
            file_path (str | None): The file path
            disabled (bool) = False: The initial enabled/disabled state.
        """

        self.__icon_factory = icon_factory

        super().__init__(prompt=self.get_prompt, disabled=disabled)
        self.label = label
        self.file_path = file_path

    def get_prompt(self) -> Content:
        if self.__icon_factory is None:
            return Content(self.label)
        return _get_cached_icon(self.__icon_factory()) + Content.from_markup(self.label)


class PathDropdownItem(DropdownItem):
    def __init__(self, completion: str, path: str) -> None:
        icon = icon_utils.get_icon_for_folder(path)
        prefix = _get_cached_icon(icon)
        super().__init__(completion, prefix)
        self.path = path


class PaddedOption(Option):
    def __init__(self, prompt: VisualType) -> None:
        if isinstance(prompt, str):
            icon = icon_utils.get_icon_smart(prompt)
            icon = (icon[0], icon[1])
            # the icon is under the assumption that the user has navigated to
            # the directory with the file, which means they rendered the icon
            # for the file already, so theoretically, no need to re-render it here
            prompt = _get_cached_icon(icon) + Content(prompt)
        super().__init__(prompt)


class PasteScreenOption(Option):
    def __init__(self, loc: VisualType, copy_or_cut: Literal["copy", "cut"]) -> None:
        if isinstance(loc, str):
            icon = icon_utils.get_icon_smart(loc)
            icon = (icon[0], icon[1])

            copy_cut_icon = icon_utils.get_icon("general", copy_or_cut)[0]
            # check existence of file, and if so, turn it red
            basename = path.basename(path.normpath(loc))
            if (
                basename
                and path.exists(path.join(getcwd(), basename))
                and copy_or_cut == "copy"
            ):
                icon_content = Content.from_markup(f"[$error]{copy_cut_icon}[/]")
            else:
                icon_content = Content(copy_cut_icon)
            loc = Content(" ") + icon_content + _get_cached_icon(icon) + Content(loc)
        super().__init__(loc)
        self.copy_or_cut = copy_or_cut
