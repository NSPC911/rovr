import pytest
from textual import events
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, VerticalGroup
from textual.widgets import Input, Static

import rovr.monkey_patches._textual  # noqa: F401


class InputApp(App):
    def compose(self) -> ComposeResult:
        yield Input()


@pytest.mark.asyncio
async def test_input_does_not_consume_modified_printable_key() -> None:
    async with InputApp().run_test() as pilot:
        input = pilot.app.query_one(Input)

        await input._on_key(events.Key("ctrl+j", "j"))
        await input._on_key(events.Key("j", "j"))

        assert input.value == "j"


class ScrollbarApp(App):
    CSS = """
    #border {
        width: 20;
        height: 10;
        border: round red;
    }
    ScrollableContainer {
        width: 1fr;
        height: 1fr;
        scrollbar-size: 1 1;
    }
    Static { width: 40; height: 20; }
    """

    def compose(self) -> ComposeResult:
        with VerticalGroup(id="border"):
            yield ScrollableContainer(Static(), id="scrollable")


@pytest.mark.asyncio
async def test_scrollbars_overlay_border() -> None:
    async with ScrollbarApp().run_test() as pilot:
        await pilot.pause()
        scrollable = pilot.app.query_one("#scrollable", ScrollableContainer)
        border = pilot.app.query_one("#border", VerticalGroup)

        assert scrollable.horizontal_scrollbar.region.bottom == border.region.bottom
        assert scrollable.vertical_scrollbar.region.right == border.region.right
        assert not scrollable.scrollbar_corner.region
        for scrollbar in (
            scrollable.horizontal_scrollbar,
            scrollable.vertical_scrollbar,
        ):
            geometry = pilot.app.screen._compositor.full_map[scrollbar]
            assert geometry.visible_region == geometry.region
