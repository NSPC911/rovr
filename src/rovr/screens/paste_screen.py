from os import getcwd, path
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.content import Content
from textual.visual import VisualType
from textual.widgets import Button, Label, Switch
from textual.widgets.option_list import Option

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.components import SpecialOptionList
from rovr.functions import icons as icon_utils

from .yes_or_no import YesOrNo, dont_ask_bind, no_bind, yes_bind


class SpecialOption(Option):
    def __init__(self, loc: VisualType, copy_or_cut: Literal["copy", "cut"]) -> None:
        if isinstance(loc, str):
            icon = icon_utils.get_icon_smart(loc)
            icon = (icon[0], icon[1])

            copy_cut_icon = icon_utils.get_icon("general", copy_or_cut)[0]
            # check existence of file, and if so, turn it red
            if (
                path.exists(path.join(getcwd(), path.basename(loc)))
                and copy_or_cut == "copy"
            ):
                icon_content = Content.from_markup(f"[$error]{copy_cut_icon}[/]")
            else:
                icon_content = Content(copy_cut_icon)
            loc = (
                Content(" ")
                + icon_content
                # the icon is under the assumption that the user has navigated to
                # the directory with the file, which means they rendered the icon
                # for the file already, so theoretically, no need to re-render it here
                + FileListSelectionWidget._icon_content_cache.get(
                    icon, Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
                )
                + Content(loc)
            )
        super().__init__(loc)


class PasteScreen(YesOrNo):
    def __init__(
        self,
        message: str,
        paths: dict[Literal["copy", "cut"], list[str]],
        destructive: bool = False,
        with_toggle: bool = False,
        border_title: str = "",
        border_subtitle: str = "",
    ) -> None:
        super().__init__(
            message, destructive, with_toggle, border_title, border_subtitle
        )
        self.paths = paths

    def compose(self) -> ComposeResult:
        with Grid(id="dialog", classes="paste"):
            with VerticalGroup(id="question_container"):
                for message in self.message.splitlines():
                    yield Label(message, classes="question")
            yield Button(
                f"\\[{yes_bind}] Yes",
                variant="error" if self.destructive else "success",
                id="yes",
            )
            yield Button(
                f"\\[{no_bind}] No",
                variant="success" if self.destructive else "error",
                id="no",
            )
            if self.with_toggle:
                with HorizontalGroup(id="dontAskAgain"):
                    yield Switch()
                    yield Label(f"\\[{dont_ask_bind}] Don't ask again")

    def on_mount(self) -> None:
        options = [SpecialOption(path, "copy") for path in self.paths["copy"]] + [
            SpecialOption(path, "cut") for path in self.paths["cut"]
        ]
        self.query_one("#dialog").mount(
            SpecialOptionList(*options),
            after=self.query_one("#question_container", VerticalGroup),
        )
        return super().on_mount()
