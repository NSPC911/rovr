from typing import Literal

from textual.containers import VerticalGroup
from textual.content import Content
from textual.visual import VisualType
from textual.widgets.option_list import Option

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.components import SpecialOptionList
from rovr.functions import icons as icon_utils

from .yes_or_no import YesOrNo


class SpecialOption(Option):
    def __init__(self, loc: VisualType, copy_or_cut: Literal["copy", "cut"]) -> None:
        if isinstance(loc, str):
            icon = icon_utils.get_icon_smart(loc)
            icon = (icon[0], icon[1])
            loc = (
                Content(" ")
                + Content(icon_utils.get_icon("general", copy_or_cut)[0])
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
        reverse_color: bool = False,
        with_toggle: bool = False,
        border_title: str = "",
        border_subtitle: str = "",
    ) -> None:
        super().__init__(
            message, reverse_color, with_toggle, border_title, border_subtitle
        )
        self.paths = paths

    def on_mount(self) -> None:
        options = [SpecialOption(path, "copy") for path in self.paths["copy"]] + [
            SpecialOption(path, "cut") for path in self.paths["cut"]
        ]
        self.query_one("#dialog").mount(
            SpecialOptionList(*options),
            after=self.query_one("#question_container", VerticalGroup),
        )
        return super().on_mount()
