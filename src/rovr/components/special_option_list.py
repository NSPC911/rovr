from textual.content import Content
from textual.visual import VisualType
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from rovr.classes.textual_options import FileListSelectionWidget
from rovr.functions import icons as icons_utils
from rovr.variables.constants import vindings


class PaddedOption(Option):
    def __init__(self, prompt: VisualType) -> None:
        if isinstance(prompt, str):
            icon = icons_utils.get_icon_smart(prompt)
            icon = (icon[0], icon[1])
            prompt = FileListSelectionWidget._icon_content_cache.get(
                icon, Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
            ) + Content(prompt)
        super().__init__(prompt)


class SpecialOptionList(OptionList):
    BINDINGS = list(vindings)
