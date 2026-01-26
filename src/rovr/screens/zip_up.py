from asyncio import sleep
from typing import ClassVar

from pathvalidate import sanitize_filepath
from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import HorizontalGroup
from textual.widgets import Input, SelectionList
from textual.widgets.selection_list import Selection

from rovr.classes.mixins import CheckboxRenderingMixin
from rovr.functions import icons as icon_utils
from rovr.variables.constants import vindings

from .input import ModalInput


class ZipTypes(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self) -> None:
        super().__init__(
            Selection("Zip     (.zip)", value="zip"),
            Selection("Tar     (.tar)", value="tar"),
            Selection("Tar Gz  (.tar.gz)", value="tar_gz"),
            Selection("Tar Bz2 (.tar.bz2)", value="tar_bz2"),
            Selection("Tar Xz  (.tar.xz)", value="tar_xz"),
            Selection("Tar Zst (.tar.zst)", value="tar_zst"),
            id="file_search_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "zip options"
        self.select(self.get_option_at_index(0))

    def _get_checkbox_icon_set(self) -> list[str]:
        """
        Get the set of icons to use for checkbox rendering.

        ContentSearchToggles uses a different icon set (missing right icon).

        Returns:
            List of icon strings for left, inner, right, and spacing.
        """
        return [
            icon_utils.get_toggle_button_icon("left"),
            icon_utils.get_toggle_button_icon("inner"),
            "",  # No right icon for ContentSearchToggles
            " ",
        ]

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        self.deselect_all()
        self.select(self.get_option_at_index(event.selection_index))


class ZipCompression(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(vindings)

    def __init__(self) -> None:
        super().__init__(
            *[Selection(str(level), value=str(level)) for level in range(0, 10)],
            id="zip_compression_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "compression level"
        self.select(self.get_option_at_index(0))

    def _get_checkbox_icon_set(self) -> list[str]:
        """
        Get the set of icons to use for checkbox rendering.

        ContentSearchToggles uses a different icon set (missing right icon).

        Returns:
            List of icon strings for left, inner, right, and spacing.
        """
        return [
            icon_utils.get_toggle_button_icon("left"),
            icon_utils.get_toggle_button_icon("inner"),
            "",  # No right icon for ContentSearchToggles
            " ",
        ]

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        self.deselect_all()
        self.select(self.get_option_at_index(event.selection_index))


class ZipUpScreen(ModalInput[tuple[str, str, int]]):
    def __init__(
        self,
        border_title: str,
        border_subtitle: str = "",
        initial_value: str = "",
        validators: list = [],
        is_path: bool = False,
        is_folder: bool = False,
    ) -> None:
        super().__init__(
            border_title, border_subtitle, initial_value, validators, is_path, is_folder
        )

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with HorizontalGroup():
            yield ZipTypes()
            yield ZipCompression()

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if (
            not self.query_one(Input).is_valid
            and event.validation_result
            and event.validation_result.failures
        ):
            # shake
            for _ in range(2):
                self.horizontal_group.styles.offset = (1, 0)
                await sleep(0.1)
                self.horizontal_group.styles.offset = (0, 0)
                await sleep(0.1)
            return
        return_path = (
            sanitize_filepath(event.input.value) if self.is_path else event.input.value
        )
        if event.input.value.endswith(("/", "\\")) and not return_path.endswith((
            "/",
            "\\",
        )):
            return_path += "/"
        self.dismiss((
            return_path,
            self.query_one(ZipTypes).selected[0],
            int(self.query_one(ZipCompression).selected[0]),
        ))
