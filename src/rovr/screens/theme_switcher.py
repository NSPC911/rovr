from importlib import resources  # noqa: F401
from pathlib import Path  # noqa: F401

from textual.app import ComposeResult
from textual.containers import VerticalGroup

from rovr.components import DoubleClickableOptionList, ModalSearchScreen, SearchInput
from rovr.variables.maps import VAR_TO_DIR  # noqa: F401


def get_themes() -> list[str]:  # ty: ignore
    # check out available themes
    ...


class ThemeSwitcherScreen(ModalSearchScreen):
    def compose(self) -> ComposeResult:
        with VerticalGroup(id="theme_switcher_group", classes="modal_search_group"):
            yield SearchInput(
                id="theme_switcher_input",
                placeholder="Search Themes...",
            )
            yield DoubleClickableOptionList(id="theme-switcher-option-list")
