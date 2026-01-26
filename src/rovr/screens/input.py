from asyncio import sleep

from pathvalidate import sanitize_filepath
from textual import events, work
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.content import Content
from textual.screen import ModalScreen
from textual.validation import Length
from textual.widgets import Input, Label

from rovr.functions import icons as icon_utils


class ModalInput(ModalScreen):
    def __init__(
        self,
        border_title: str,
        border_subtitle: str = "",
        initial_value: str = "",
        validators: list = [],
        is_path: bool = False,
        is_folder: bool = False,
    ) -> None:
        super().__init__()
        self.border_title = border_title
        self.border_subtitle = border_subtitle
        self.initial_value = initial_value
        length_checker = Length(minimum=1, failure_description="A value is required.")
        length_checker.strict = True
        self.validators = [length_checker] + validators
        self.is_path = is_path
        self.is_folder = is_folder
        if self.is_path:
            self.icon_widget = Label(
                f"> {icon_utils.get_icon('file', 'default')[0]} ",
                id="icon",
                shrink=True,
                classes="system",
            )
        else:
            self.icon_widget = Label("> ", id="icon", shrink=True, classes="arrow")

    def compose(self) -> ComposeResult:
        with HorizontalGroup(id="modalInput_group"):
            yield self.icon_widget
            yield Input(
                id="input",
                compact=True,
                value=self.initial_value,
                valid_empty=False,
                validators=self.validators,
                # ty ignore because a list is iterable,
                # but it is crashing out, because it thinks
                # lists aren't iterable, weird
                validate_on=[
                    "changed",
                    "submitted",
                ],  # ty: ignore[invalid-argument-type]
            )

    @work(exclusive=True)
    async def on_input_changed(self, event: Input.Changed) -> None:
        if self.is_path:
            if (
                event.value == self.initial_value and event.value != ""
            ) or self.query_one(Input).is_valid:
                self.icon_widget.classes = "valid"
                self.horizontal_group.classes = "valid"
                self.horizontal_group.border_subtitle = self.border_subtitle
            else:
                self.icon_widget.classes = "invalid"
                self.horizontal_group.classes = "invalid"
                if event.validation_result:
                    try:
                        self.horizontal_group.border_subtitle = str(
                            event.validation_result.failure_descriptions[0]
                        )
                    except IndexError:
                        # I got an error from this, but it couldn't
                        # be properly printed, so I'm leaving this here
                        # in case someone else gets the same issue
                        # so that they can create a new issue ^_^
                        raise IndexError(
                            f"Empty failure description.\nIf you see this, create an issue, thanks!\n{event.validation_result=}, {event.value=}"
                        ) from None
                else:
                    # valid_empty = False
                    self.horizontal_group.border_subtitle = (
                        "The value must not be empty!"
                    )
            if event.value.replace("\\", "/").endswith("/"):
                # dir
                icon = icon_utils.get_icon_for_folder(event.value[:-1])
            elif self.is_folder:
                # dir
                icon = icon_utils.get_icon_for_folder(event.value)
            else:
                # file
                icon = icon_utils.get_icon_for_file(event.value)
            self.icon_widget.update(
                Content.from_markup(f"> [{icon[1]}]{icon[0]}[{icon[1]}] ")
            )

    def on_mount(self) -> None:
        self.horizontal_group: HorizontalGroup = self.query_one(HorizontalGroup)
        inp: Input = self.query_one(Input)
        self.horizontal_group.border_title = self.border_title
        if self.border_subtitle != "":
            self.horizontal_group.border_subtitle = self.border_subtitle
        inp.focus()
        inp.validate(inp.value)
        self.on_input_changed(inp.Changed(inp, inp.value))

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
        self.dismiss(return_path)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to dismiss the dialog."""
        if event.key == "escape":
            event.stop()
            self.dismiss("")

    def on_click(self, event: events.Click) -> None:
        if event.widget is self:
            # ie click outside
            event.stop()
            self.dismiss("")
