from textual import events
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
            # the icon is under the assumption that the user has navigated to
            # the directory with the file, which means they rendered the icon
            # for the file already, so theoretically, no need to re-render it here
            prompt = FileListSelectionWidget._icon_content_cache.get(
                icon, Content.from_markup(f" [{icon[1]}]{icon[0]}[/{icon[1]}] ")
            ) + Content(prompt)
        super().__init__(prompt)


class DoubleClickableOptionList(OptionList):
    async def _on_click(self, event: events.Click) -> None:
        """React to the mouse being clicked on an item.

        Args:
            event: The click event.
        """
        event.prevent_default()
        clicked_option: int | None = event.style.meta.get("option")
        if clicked_option is not None and not self._options[clicked_option].disabled:
            if event.chain == 2:
                if self.highlighted != clicked_option:
                    self.highlighted = clicked_option
                self.action_select()
            else:
                self.highlighted = clicked_option
        if self.screen.focused and getattr(self.screen, "search_input", False):
            self.screen.search_input.focus()


class SpecialOptionList(OptionList):
    BINDINGS = list(vindings)
