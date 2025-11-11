from contextlib import suppress
from os import path
from typing import TypedDict

import toml
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget

from rovr.functions.config import get_version
from rovr.variables.maps import VAR_TO_DIR


class StateDict(TypedDict):
    current_version: str
    pinned_sidebar_visible: bool
    preview_sidebar_visible: bool
    footer_visible: bool
    menuwrapper_visible: bool


class StateManager(Widget):
    DEFAULT_CSS = """
    StateManager {
        display: none;
    }
    """

    pinned_sidebar_visible: reactive[bool] = reactive(True, init=False)
    preview_sidebar_visible: reactive[bool] = reactive(True, init=False)
    footer_visible: reactive[bool] = reactive(True, init=False)
    menuwrapper_visible: reactive[bool] = reactive(True, init=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state_file: str = path.join(VAR_TO_DIR["CONFIG"], "state.toml")
        self.current_version: str = get_version()
        self.previous_version: str | None = None
        self._is_loading = True
        self._load_state()
        self._is_loading = False

    def _load_state(self) -> None:
        if path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded_state: StateDict = toml.load(f)
                    # Check for version change
                    # TODO: do something with this later, maybe for messages
                    # or breaking changes <- need to refactor config because
                    #                        currently config is too strict
                    #                        and doesnt load when fail
                    file_version = loaded_state.get("current_version")
                    if file_version and file_version != self.current_version:
                        self.previous_version = file_version

                    self.pinned_sidebar_visible = loaded_state.get(
                        "pinned_sidebar_visible", True
                    )
                    self.preview_sidebar_visible = loaded_state.get(
                        "preview_sidebar_visible", True
                    )
                    self.footer_visible = loaded_state.get("footer_visible", True)
                    self.menuwrapper_visible = loaded_state.get(
                        "menuwrapper_visible", True
                    )
            except (toml.TomlDecodeError, OSError, KeyError):
                self._create_default_state()
        else:
            self._create_default_state()

    def _create_default_state(self) -> None:
        self.set_reactive(StateManager.pinned_sidebar_visible, True)
        self.set_reactive(StateManager.preview_sidebar_visible, True)
        self.set_reactive(StateManager.footer_visible, True)
        self.set_reactive(StateManager.menuwrapper_visible, True)
        self._save_state()

    def _save_state(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                state: StateDict = {
                    "current_version": self.current_version,
                    "pinned_sidebar_visible": self.pinned_sidebar_visible,
                    "preview_sidebar_visible": self.preview_sidebar_visible,
                    "footer_visible": self.footer_visible,
                    "menuwrapper_visible": self.menuwrapper_visible,
                }
                toml.dump(state, f)
        except OSError:
            pass

    def watch_pinned_sidebar_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        with suppress(NoMatches):
            pinned_sidebar = self.app.query_one("#pinned_sidebar_container")
            if visible:
                pinned_sidebar.remove_class("hide")
            else:
                pinned_sidebar.add_class("hide")
        self._save_state()

    def watch_preview_sidebar_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        with suppress(NoMatches):
            preview_sidebar = self.app.query_one("PreviewContainer")
            if visible:
                preview_sidebar.remove_class("hide")
            else:
                preview_sidebar.add_class("hide")
        self._save_state()

    def watch_footer_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        with suppress(NoMatches):
            footer = self.app.query_one("#footer")
            if visible:
                footer.remove_class("hide")
            else:
                footer.add_class("hide")
        self._save_state()

    def watch_menuwrapper_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        with suppress(NoMatches):
            menuwrapper = self.app.query_one("#menuwrapper")
            if visible:
                menuwrapper.remove_class("hide")
            else:
                menuwrapper.add_class("hide")
        self._save_state()

    def toggle_pinned_sidebar(self) -> None:
        self.pinned_sidebar_visible = not self.pinned_sidebar_visible

    def toggle_preview_sidebar(self) -> None:
        self.preview_sidebar_visible = not self.preview_sidebar_visible

    def toggle_footer(self) -> None:
        self.footer_visible = not self.footer_visible

    def toggle_menuwrapper(self) -> None:
        self.menuwrapper_visible = not self.menuwrapper_visible

    def restore_state(self) -> None:
        self._is_loading = False
        self.watch_pinned_sidebar_visible(self.pinned_sidebar_visible)
        self.watch_preview_sidebar_visible(self.preview_sidebar_visible)
        self.watch_footer_visible(self.footer_visible)
        self.watch_menuwrapper_visible(self.menuwrapper_visible)
