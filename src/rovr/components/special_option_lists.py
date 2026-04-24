from textual import events

from rovr.classes.mixins import ScrollOffMixin, SingleLineOptionLayoutMixin
from rovr.classes.textual_options import PaddedOption
from rovr.variables.constants import bindings
from rovr.widgets import OptionList


class DoubleClickableOptionList(SingleLineOptionLayoutMixin, OptionList):
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


class DoubleClickableScrollOffOptionList(ScrollOffMixin, DoubleClickableOptionList): ...


class SpecialOptionList(OptionList):
    BINDINGS = list(bindings)


__all__ = [
    "DoubleClickableOptionList",
    "DoubleClickableScrollOffOptionList",
    "SpecialOptionList",
    "PaddedOption",
]
