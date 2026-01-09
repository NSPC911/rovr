from os import getcwd, path

from rich.style import Style
from textual import on
from textual.app import ComposeResult, RenderResult
from textual.await_complete import AwaitComplete
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.renderables.bar import Bar as BarRenderable
from textual.widget import Widget
from textual.widgets import Button, Input, Tabs
from textual.widgets._tabs import Tab, Underline
from textual.widgets.option_list import OptionDoesNotExist

from rovr.classes import SessionManager
from rovr.functions.path import normalise


class BetterBarRenderable(BarRenderable):
    HALF_BAR_LEFT: str = "╶"
    BAR: str = "─"
    HALF_BAR_RIGHT: str = "╴"


class BetterUnderline(Underline):
    def render(self) -> RenderResult:
        """Render the bar.
        Returns:
            RenderResult: the result of the render method"""
        bar_style = self.get_component_rich_style("underline--bar")
        return BetterBarRenderable(
            highlight_range=self._highlight_range,
            highlight_style=Style.from_color(bar_style.color),
            background_style=Style.from_color(bar_style.bgcolor),
        )


class TablineTab(Tab):
    ALLOW_SELECT = False

    def __init__(self, directory: str | bytes = "", label: str = "") -> None:
        """Initialise a Tab.

        Args:
            directory (str): The directory to set the tab as.
            label (ContentText): The label to use in the tab.
        """
        if directory == "":
            directory = getcwd()
        directory = normalise(directory)
        if label == "":
            label = str(
                path.basename(directory)
                if path.basename(directory) != ""
                else directory.strip("/")
            )
        super().__init__(label=label)
        self.directory = directory
        self.session = SessionManager()


class Tabline(Tabs):
    def compose(self) -> ComposeResult:
        with Container(id="tabs-scroll"), Vertical(id="tabs-list-bar"):
            with Horizontal(id="tabs-list"):
                yield from self._tabs
            yield BetterUnderline()

    async def add_tab(  # ty: ignore[invalid-method-override]
        self,
        directory: str = "",
        label: str = "",
        before: Tab | str | None = None,
        after: Tab | str | None = None,
    ) -> None:
        """Add a new tab to the end of the tab list.

        Args:
            directory (str): The directory to set the tab as.
            label (ContentText): The label to use in the tab.
            before: Optional tab or tab ID to add the tab before.
            after: Optional tab or tab ID to add the tab after.

        Note:
            Only one of `before` or `after` can be provided. If both are
            provided a `Tabs.TabError` will be raised.
        """
        """
        Returns:
            An optionally awaitable object that waits for the tab to be mounted and
                internal state to be fully updated to reflect the new tab.
        Raises:
            Tabs.TabError: If there is a problem with the addition request.
        """

        tab = TablineTab(directory=directory, label=label)
        await super().add_tab(tab, before=before, after=after)
        self._activate_tab(tab)
        # redo max-width
        self.parent.on_resize()

    def remove_tab(self, tab_or_id: Tab | str | None) -> AwaitComplete:
        """Remove a tab.

        Args:
            tab_or_id: The Tab to remove or its id.

        Returns:
            An optionally awaitable object that waits for the tab to be removed.
        """
        if not tab_or_id:
            return AwaitComplete()

        if isinstance(tab_or_id, Tab):
            remove_tab = tab_or_id
        else:
            try:
                remove_tab = self.query_one(f"#tabs-list > #{tab_or_id}", Tab)
            except NoMatches:
                return AwaitComplete()

        next_tab = self._next_active if remove_tab.has_class("-active") else None

        async def do_remove() -> None:
            """Perform the remove after refresh so the underline bar gets new positions."""
            await remove_tab.remove()
            if not self.query("#tabs-list > Tab"):
                self.active = ""
            elif next_tab is not None:
                self.active = next_tab.id or ""
            else:
                self._highlight_active(animate=False)
            self.parent.on_resize()

        return AwaitComplete(do_remove())

    @on(Tab.Clicked)
    @on(Tabs.TabActivated)
    async def check_tab_click(self, event: TablineTab.Clicked) -> None:
        assert isinstance(event.tab, TablineTab)

        def callback() -> None:
            assert isinstance(event.tab, TablineTab)
            file_list: Widget = self.app.query_one("#file_list")
            assert isinstance(file_list.input, Input)
            file_list.select_mode_enabled = event.tab.session.selectMode
            if event.tab.session.selectMode:
                for option in event.tab.session.selectedItems:
                    try:
                        file_list.select(file_list.get_option(option))
                        self.log(f"Successfully selected option: {option}")
                    except (OptionDoesNotExist, AttributeError) as e:
                        self.log(f"Failed to select option {option}: {e}")
            if event.tab.session.search != "":
                file_list.input.value = event.tab.session.search

        self.app.cd(event.tab.directory, add_to_history=False, callback=callback)


class NewTabButton(Button):
    def __init__(self) -> None:
        super().__init__(label="+", variant="primary", compact=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        assert self.parent and self.parent.parent
        await self.parent.parent.query_one(Tabline).add_tab(getcwd())
