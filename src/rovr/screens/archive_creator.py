from asyncio import sleep
from typing import ClassVar, Literal, NamedTuple

from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import HorizontalGroup
from textual.widgets import Input, SelectionList
from textual.widgets.selection_list import Selection

from rovr.classes.mixins import CheckboxRenderingMixin, SetOptionsSelectionList
from rovr.functions.utils import dismiss
from rovr.variables.constants import bindings

from .input import ModalInput


class ArchiveTypes(CheckboxRenderingMixin, SelectionList, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(
            Selection("Zip     (.zip)", value="zip"),
            Selection("Tar     (.tar)", value="tar"),
            Selection("Tar Gz  (.tar.gz)", value="tar.gz"),
            Selection("Tar Bz2 (.tar.bz2)", value="tar.bz2"),
            Selection("Tar Xz  (.tar.xz)", value="tar.xz"),
            Selection("Tar Zst (.tar.zst)", value="tar.zst"),
            id="archive_types_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "Archive Formats"
        self.select(self.get_option_at_index(0))

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        # not using self.deselect_all to prevent a refresh
        with self.prevent(ArchiveTypes.SelectedChanged):
            for option in self._options:
                self._deselect(option.value)
        self.select(self.get_option_at_index(event.selection_index))
        self.parent.query_one(ArchiveCompression).update_compressions(
            self.get_option_at_index(event.selection_index).value
        )


class ArchiveCompression(
    CheckboxRenderingMixin,
    SetOptionsSelectionList,
    SelectionList,
    inherit_bindings=False,
):
    BINDINGS: ClassVar[list[BindingType]] = list(bindings)

    def __init__(self) -> None:
        super().__init__(
            # default 0-10
            *[Selection(str(level), value=str(level)) for level in range(0, 10)],
            id="archive_compression_toggles",
        )

    def on_mount(self) -> None:
        self.border_title = "Compression Levels"
        self.select(self.get_option_at_index(0))

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        # not using self.deselect_all to prevent a refresh
        with self.prevent(ArchiveCompression.SelectedChanged):
            for option in self._options:
                self._deselect(option.value)
        self.select(self.get_option_at_index(event.selection_index))

    def update_compressions(
        self, algo: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"]
    ) -> None:
        """Update compression levels based on selected algorithm."""
        if algo == "zip" or algo == "tar.gz" or algo == "tar.xz":
            self.set_options(
                Selection(str(level), value=str(level)) for level in range(0, 10)
            )
        elif algo == "tar.bz2":
            self.set_options(
                Selection(str(level), value=str(level)) for level in range(1, 10)
            )
        elif algo == "tar.zst":
            self.set_options(
                Selection(str(level), value=str(level)) for level in range(1, 23)
            )
        else:
            self.set_options([Selection("  NIL", value="0", disabled=True)])

        self.refresh()
        if self.options:
            self.select(self.get_option_at_index(0))


class ArchiveCreationScreen(ModalInput):
    class ReturnType(NamedTuple):
        path: str
        algo: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"]
        level: int

    BINDINGS = [
        Binding("tab", "app.focus_next", "Focus Next", show=False),
        Binding("shift+tab", "app.focus_previous", "Focus Previous", show=False),
        Binding("ctrl+c,super+c", "screen.copy_text", "Copy selected text", show=False),
    ]

    def __init__(
        self,
        initial_value: str = "",
        validators: list | None = None,
        is_path: bool = False,
    ) -> None:
        if validators is None:
            validators = []
        super().__init__("Create Archive", "", initial_value, validators, is_path)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with HorizontalGroup(id="archive_options_group"):
            yield ArchiveTypes()
            yield ArchiveCompression()

    @work
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        from pathvalidate import sanitize_filepath

        event.prevent_default()
        event.stop()
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
        compression_selection = self.query_one(ArchiveCompression).selected
        dismiss(
            self,
            ArchiveCreationScreen.ReturnType(
                return_path,
                self.query_one(ArchiveTypes).selected[0],
                int(compression_selection[0] if compression_selection else 0),
            ),
            event,
        )

    @on(ArchiveTypes.SelectionToggled, "ArchiveTypes")
    def zip_type_toggled(self, event: ArchiveTypes.SelectionToggled) -> None:
        """Handle zip type selection toggling."""
        input_widget = self.query_one(Input)
        base = ".".join(input_widget.value.split(".")[:-1])
        if base.endswith(".tar"):
            base = ".".join(base.split(".")[:-1])
        input_widget.value = f"{base}.{event.selection.value}"

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to dismiss the dialog."""
        if event.key == "escape":
            dismiss(self, None, event)

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            dismiss(self, None, event)
