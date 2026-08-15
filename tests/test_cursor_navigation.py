import pytest
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import OptionList, SelectionList
from textual.widgets.option_list import Option
from textual.widgets.selection_list import Selection

from rovr.classes.mixins import CursorNavigationMixin, SelectionNavigationMixin


class CursorList(CursorNavigationMixin, OptionList): ...


class SelectionCursorList(SelectionNavigationMixin, SelectionList): ...


class CursorApp(App[None]):
    CSS = "CursorList { height: 10; }"

    def __init__(self, options: list[Option | str]) -> None:
        super().__init__()
        self.options = options
        self.highlighted_messages = 0

    def compose(self) -> ComposeResult:
        yield CursorList(*self.options)

    @on(OptionList.OptionHighlighted)
    def count_highlights(self) -> None:
        self.highlighted_messages += 1


class SelectionCursorApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.highlighted_messages = 0
        self.selected_messages = 0

    def compose(self) -> ComposeResult:
        yield SelectionCursorList(*(Selection(str(index), index) for index in range(8)))

    @on(SelectionList.SelectionHighlighted)
    def count_highlights(self) -> None:
        self.highlighted_messages += 1

    @on(SelectionList.SelectedChanged)
    def count_selected(self) -> None:
        self.selected_messages += 1


@pytest.mark.asyncio
async def test_cursor_moves_once_and_skips_disabled_options() -> None:
    app = CursorApp([
        Option(str(index), disabled=index in {2, 3}) for index in range(8)
    ])

    async with app.run_test() as pilot:
        await pilot.pause()
        option_list = app.query_one(CursorList)
        app.highlighted_messages = 0

        option_list.action_cursor(4)
        await pilot.pause()

        assert option_list.highlighted == 6
        assert app.highlighted_messages == 1


@pytest.mark.asyncio
async def test_cursor_page_supports_fractional_pages() -> None:
    app = CursorApp([str(index) for index in range(30)])

    async with app.run_test() as pilot:
        await pilot.pause()
        option_list = app.query_one(CursorList)
        option_list.highlighted = 10
        await pilot.pause()
        app.highlighted_messages = 0
        expected = 10 + round(option_list.scrollable_content_region.height / 2)

        option_list.action_cursor_page(0.5)
        await pilot.pause()

        assert option_list.highlighted == expected
        assert app.highlighted_messages == 1


@pytest.mark.asyncio
async def test_select_cursor_batches_selection_and_highlight_messages() -> None:
    app = SelectionCursorApp()

    async with app.run_test() as pilot:
        await pilot.pause()
        option_list = app.query_one(SelectionCursorList)
        app.highlighted_messages = 0

        option_list.action_select_cursor(4)
        await pilot.pause()

        assert option_list.highlighted == 4
        assert option_list.selected == [0, 1, 2, 3, 4]
        assert app.highlighted_messages == 1
        assert app.selected_messages == 1
