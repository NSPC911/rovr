import contextlib
import os

from textual import events, work
from textual.fuzzy import Matcher
from textual.types import OptionDoesNotExist
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection, SelectionError


class SearchInput(Input):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args, password=False, compact=True, select_on_focus=False, **kwargs
        )

    def on_mount(self) -> None:
        self.items_list: OptionList = self.parent.query_one(OptionList)
        self.initial_cwd = os.getcwd()

    # exclusive when too many options, and not enough time to mount
    @work(exclusive=True)
    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.value == "" and self.initial_cwd == os.getcwd():
            highlighted = self.items_list.highlighted_option
            self.items_list.clear_options()
            self.items_list.add_options(self.items_list.list_of_options)
            if highlighted is not None:
                with contextlib.suppress(OptionDoesNotExist, SelectionError):
                    self.items_list.highlighted = self.items_list.get_option_index(
                        highlighted.id
                    )
            else:
                self.items_list.highlighted = 0
            return
        elif event.value == "" and self.initial_cwd != os.getcwd():
            self.initial_cwd = os.getcwd()
            return
        self.items_list.clear_options()
        matches = []
        matcher = Matcher(
            event.value,
            match_style="underline",  # ty: ignore[invalid-argument-type]
        )
        assert hasattr(self.items_list, "list_of_options")
        for option in self.items_list.list_of_options:
            assert isinstance(option, Option)
            if option.disabled:
                matches.append(option)
                continue
            score = matcher.match(option.label)
            if score > 0:
                matches.append(option)
        if matches:
            self.items_list.add_options(matches)
        else:
            try:
                self.items_list.add_option(
                    Option("   --no-matches--", id="", disabled=True)
                )
            except SelectionError:
                self.items_list.add_option(
                    Selection("   --no-matches--", value="", id="", disabled=True)
                )
        if self.items_list.highlighted is None:
            self.items_list.action_cursor_down()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.items_list.focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.items_list.focus()
            event.stop()
