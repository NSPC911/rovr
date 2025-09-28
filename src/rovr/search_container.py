import contextlib

from textual import events, work
from textual.css.query import NoMatches
from textual.fuzzy import Matcher
from textual.types import OptionDoesNotExist
from textual.widgets import Input, OptionList, SelectionList
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection, SelectionError

from rovr.functions.utils import set_scuffed_subtitle


class SearchInput(Input):
    def __init__(self, always_add_disabled: bool = True, *args, **kwargs) -> None:
        super().__init__(
            *args, password=False, compact=True, select_on_focus=False, **kwargs
        )
        self.always_add_disabled = always_add_disabled
        self.selected = set()

    def on_mount(self) -> None:
        self.items_list = self.parent.query_one(OptionList)
        if isinstance(self.items_list, SelectionList):
            self.item_list_type = "Selection"
        elif isinstance(self.items_list, OptionList):
            self.item_list_type = "Option"
        else:
            raise NoMatches(
                f"type {type(self.items_list).__name__} was matched but expected either OptionList or SelectionList"
            )

    # exclusive when too many options, and not enough time to mount
    @work(exclusive=True)
    async def on_input_changed(self, event: Input.Changed) -> None:
        if self.item_list_type == "Selection":
            assert isinstance(self.items_list, SelectionList)
            self.selected.update({*self.items_list.selected})
        else:
            assert isinstance(self.items_list, OptionList)
        try:
            highlighted = self.items_list.highlighted_option.id
        except AttributeError:
            highlighted = None
        self.app.tabWidget.active_tab.session.search = event.value
        if event.value == "":
            self.items_list.clear_options()
            self.items_list.add_options(self.items_list.list_of_options)
            if highlighted is not None:
                with contextlib.suppress(OptionDoesNotExist, SelectionError):
                    self.items_list.highlighted = self.items_list.get_option_index(
                        highlighted
                    )
            else:
                self.items_list.highlighted = 0
            if self.item_list_type == "Selection":
                for option_id in self.selected:
                    with contextlib.suppress(OptionDoesNotExist):
                        if not self.items_list.select_mode_enabled:
                            with self.items_list.prevent(
                                self.items_list.SelectedChanged
                            ):
                                self.items_list.select(
                                    self.items_list.get_option(option_id)
                                )
                        else:
                            self.items_list.select(
                                self.items_list.get_option(option_id)
                            )
            return
        self.items_list.clear_options()
        matches = []
        matcher = Matcher(
            event.value,
        )
        assert hasattr(self.items_list, "list_of_options")
        for option in self.items_list.list_of_options:
            assert isinstance(option, Option)
            if self.always_add_disabled and option.disabled:
                matches.append(option)
                continue
            score = matcher.match(option.label)
            if score > 0:
                matches.append(option)
        if matches:
            self.items_list.add_options(matches)
        else:
            if self.item_list_type == "Option":
                self.items_list.add_option(
                    Option("   --no-matches--", id="", disabled=True)
                )
            else:
                self.items_list.add_option(
                    Selection("   --no-matches--", value="", id="", disabled=True)
                )
                set_scuffed_subtitle(
                    self.items_list.parent,
                    "SELECT" if self.items_list.select_mode_enabled else "NORMAL",
                    "0/0",
                )
        if self.items_list.highlighted is None:
            if highlighted is not None:
                try:
                    self.items_list.highlighted = self.items_list.get_option_index(
                        highlighted
                    )
                except OptionDoesNotExist:
                    self.items_list.action_cursor_down()
            else:
                self.items_list.action_cursor_down()
        if self.item_list_type == "Selection":
            for option_id in self.selected:
                with contextlib.suppress(OptionDoesNotExist):
                    if not self.items_list.select_mode_enabled:
                        with self.items_list.prevent(self.items_list.SelectedChanged):
                            self.items_list.select(
                                self.items_list.get_option(option_id)
                            )
                    else:
                        self.items_list.select(self.items_list.get_option(option_id))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.items_list.focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.items_list.focus()
            event.stop()

    def clear_selected(self) -> None:
        self.selected = set()
