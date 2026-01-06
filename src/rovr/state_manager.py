from contextlib import suppress
from os import path
from typing import Literal, TypedDict, cast

import tomli
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget

from rovr.functions.config import get_version
from rovr.functions.folder_prefs import (
    get_folder_pref,
    load_folder_prefs,
    remove_folder_pref,
    set_folder_pref,
)
from rovr.functions.path import normalise
from rovr.variables.constants import SortByOptions
from rovr.variables.maps import VAR_TO_DIR


class StateDict(TypedDict):
    current_version: str
    pinned_sidebar_visible: bool
    preview_sidebar_visible: bool
    footer_visible: bool
    menuwrapper_visible: bool
    sort_by: SortByOptions
    sort_descending: bool


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
    sort_by: reactive[str] = reactive("name", init=False)
    sort_descending: reactive[bool] = reactive(False, init=False)
    custom_sort_enabled: reactive[bool] = reactive(False, init=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state_file: str = path.join(VAR_TO_DIR["CONFIG"], "state.toml")
        self.current_version: str = get_version()
        self.previous_version: str | None = None
        self._skip_save = True
        self._is_loading = False
        self._current_folder: str = ""  # Track current folder for custom sort
        load_folder_prefs()  # Load folder preferences at startup
        self._load_state()
        self._skip_save = False
        self._locked_by: Literal[
            "PinnedSidebar", "PreviewSidebar", "Footer", "menuwrapper", None
        ] = None

    def _load_state(self) -> None:
        self._is_loading = True
        if path.exists(self.state_file):
            try:
                with open(self.state_file, "rb") as f:
                    loaded_state: StateDict = cast(StateDict, tomli.load(f))
                    # Check for version change
                    # TODO: do something with this later, maybe for messages
                    # or breaking changes <- need to refactor config because
                    #                        currently config is too strict
                    #                        and doesnt load when fail
                    file_version = loaded_state.get("current_version")
                    if file_version and file_version != self.current_version:
                        self.previous_version = file_version

                    if self.pinned_sidebar_visible != (
                        pinned_sidebar_visible := loaded_state.get(
                            "pinned_sidebar_visible", True
                        )
                    ):
                        self.pinned_sidebar_visible = pinned_sidebar_visible
                    if self.preview_sidebar_visible != (
                        preview_sidebar_visible := loaded_state.get(
                            "preview_sidebar_visible", True
                        )
                    ):
                        self.preview_sidebar_visible = preview_sidebar_visible
                    if self.footer_visible != (
                        footer_visible := loaded_state.get("footer_visible", True)
                    ):
                        self.footer_visible = footer_visible
                    if self.menuwrapper_visible != (
                        menuwrapper_visible := loaded_state.get(
                            "menuwrapper_visible", True
                        )
                    ):
                        self.menuwrapper_visible = menuwrapper_visible
                    sort_by = loaded_state.get("sort_by", "name")
                    if sort_by not in [
                        "name",
                        "size",
                        "modified",
                        "created",
                        "extension",
                        "natural",
                    ]:
                        sort_by = "name"
                    # clearly sort_by = "name" wouldn't lead to the condition being trye
                    elif self.sort_by != sort_by:
                        self.sort_by = sort_by
                    if self.sort_descending != (
                        sort_descending := loaded_state.get("sort_descending", False)
                    ):
                        self.sort_descending = sort_descending
            except (tomli.TOMLDecodeError, OSError):
                self._create_default_state()
        else:
            self._create_default_state()
        self._is_loading = False

    def _create_default_state(self) -> None:
        self.pinned_sidebar_visible = True
        self.preview_sidebar_visible = True
        self.footer_visible = True
        self.menuwrapper_visible = True
        self.sort_by = "name"
        self.sort_descending = False
        self._save_state(force=True)

    def _save_state(self, force: bool = False) -> None:
        if self._skip_save and not force:
            return
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                # peak hardcoding
                f.write(f"""current_version = "{self.current_version}"
pinned_sidebar_visible = {str(self.pinned_sidebar_visible).lower()}
preview_sidebar_visible = {str(self.preview_sidebar_visible).lower()}
footer_visible = {str(self.footer_visible).lower()}
menuwrapper_visible = {str(self.menuwrapper_visible).lower()}
sort_by = "{self.sort_by}"
sort_descending = {str(self.sort_descending).lower()}
""")
        except (OSError, PermissionError) as exc:
            self.notify(
                f"Attempted to write state file, but {type(exc).__name__} occurred\n{exc}",
                severity="error",
            )

    def watch_pinned_sidebar_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        self._locked_by = "PinnedSidebar"
        with suppress(NoMatches):
            pinned_sidebar = self.app.query_one("#pinned_sidebar_container")
            if visible:
                pinned_sidebar.remove_class("hide")
            else:
                pinned_sidebar.add_class("hide")
        if self._locked_by == "PinnedSidebar":
            self._save_state()

    def watch_preview_sidebar_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        self._locked_by = "PreviewSidebar"
        with suppress(NoMatches):
            preview_sidebar = self.app.query_one("PreviewContainer")
            if visible:
                preview_sidebar.remove_class("hide")
            else:
                preview_sidebar.add_class("hide")
        if self._locked_by == "PreviewSidebar":
            self._save_state()

    def watch_footer_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        self._locked_by = "Footer"
        with suppress(NoMatches):
            footer = self.app.query_one("#footer")
            if visible:
                footer.remove_class("hide")
            else:
                footer.add_class("hide")
        if self._locked_by == "Footer":
            self._save_state()

    def watch_menuwrapper_visible(self, visible: bool) -> None:
        if self._is_loading:
            return
        self._locked_by = "menuwrapper"
        with suppress(NoMatches):
            menuwrapper = self.app.query_one("#menuwrapper")
            if visible:
                menuwrapper.remove_class("hide")
            else:
                menuwrapper.add_class("hide")
        if self._locked_by == "menuwrapper":
            self._save_state()

    def watch_sort_by(self, value: str) -> None:
        if self._is_loading:
            return
        # Save to folder prefs if custom sort is enabled, otherwise save global
        if self.custom_sort_enabled and self._current_folder:
            set_folder_pref(self._current_folder, value, self.sort_descending)
        else:
            self._save_state()
        # Update file list with new sort order
        with suppress(NoMatches):
            self.app.file_list.update_file_list(add_to_session=False)
        # Update sort button icon
        with suppress(NoMatches):
            self.app.query_one("#sort_order").update_icon()

    def watch_sort_descending(self, value: bool) -> None:
        if self._is_loading:
            return
        # Save to folder prefs if custom sort is enabled, otherwise save global
        if self.custom_sort_enabled and self._current_folder:
            set_folder_pref(self._current_folder, self.sort_by, value)
        else:
            self._save_state()
        with suppress(NoMatches):
            self.app.file_list.update_file_list(add_to_session=False)
        # Update sort button icon
        with suppress(NoMatches):
            self.app.query_one("#sort_order").update_icon()

    def toggle_pinned_sidebar(self) -> None:
        self.pinned_sidebar_visible = not self.pinned_sidebar_visible

    def toggle_preview_sidebar(self) -> None:
        self.preview_sidebar_visible = not self.preview_sidebar_visible

    def toggle_footer(self) -> None:
        self.footer_visible = not self.footer_visible

    def toggle_menuwrapper(self) -> None:
        self.menuwrapper_visible = not self.menuwrapper_visible

    def restore_state(self) -> None:
        # just for safe measure, set it to false
        self._is_loading = False
        self._skip_save = True
        self.watch_pinned_sidebar_visible(self.pinned_sidebar_visible)
        self.watch_preview_sidebar_visible(self.preview_sidebar_visible)
        self.watch_footer_visible(self.footer_visible)
        self.watch_menuwrapper_visible(self.menuwrapper_visible)
        self.watch_sort_by(self.sort_by)
        self.watch_sort_descending(self.sort_descending)
        self._skip_save = False

    def apply_folder_sort_prefs(self, folder_path: str) -> None:
        """
        Apply folder-specific sort preferences if they exist.
        Otherwise, keep the global sort settings.

        Args:
            folder_path: The path to the folder being navigated to.
        """
        self._current_folder = normalise(folder_path)
        folder_pref = get_folder_pref(self._current_folder)

        if folder_pref:
            # Folder has custom sort preferences
            self._is_loading = True  # Prevent triggering watchers while loading
            self.custom_sort_enabled = True
            if self.sort_by != folder_pref["sort_by"]:
                self.sort_by = folder_pref["sort_by"]
            if self.sort_descending != folder_pref["sort_descending"]:
                self.sort_descending = folder_pref["sort_descending"]
            self._is_loading = False
        else:
            # No custom preferences, use global settings
            self.custom_sort_enabled = False
            # Reload global state to ensure we're using global sort settings
            self._apply_global_sort()

    def _apply_global_sort(self) -> None:
        """Apply the global sort settings from state.toml."""
        if not path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "rb") as f:
                loaded_state: StateDict = cast(StateDict, tomli.load(f))
                sort_by = loaded_state.get("sort_by", "name")
                if sort_by not in [
                    "name",
                    "size",
                    "modified",
                    "created",
                    "extension",
                    "natural",
                ]:
                    sort_by = "name"
                sort_descending = loaded_state.get("sort_descending", False)

                self._is_loading = True
                if self.sort_by != sort_by:
                    self.sort_by = sort_by
                if self.sort_descending != sort_descending:
                    self.sort_descending = sort_descending
                self._is_loading = False
        except (tomli.TOMLDecodeError, OSError):
            pass

    def toggle_custom_sort(self) -> None:
        """
        Toggle the custom sort preference for the current folder.

        If enabling: saves current sort as the folder's custom preference.
        If disabling: removes the folder's custom preference and reverts to global.
        """
        if not self._current_folder:
            return

        if self.custom_sort_enabled:
            # Disabling: remove folder pref and revert to global
            remove_folder_pref(self._current_folder)
            self.custom_sort_enabled = False
            self._apply_global_sort()
        else:
            # Enabling: save current sort as folder pref
            set_folder_pref(self._current_folder, self.sort_by, self.sort_descending)
            self.custom_sort_enabled = True

    def get_current_folder(self) -> str:
        return self._current_folder
