from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace
from functools import lru_cache
from importlib import resources
from os import path
from time import perf_counter
from typing import Any, ClassVar, Iterable, cast

from rich.table import Table
from rich.text import Text
from textual import events, on, work
from textual.app import App
from textual.css.errors import StylesheetError
from textual.css.stylesheet import StylesheetParseError
from textual.dom import DOMNode
from textual.geometry import Offset
from textual.widgets import Static
from textual_drivers.dnd import (
    DNDDragIn,
    DNDDragInOperation,
    DNDDragOutOperation,
    DragOutFinished,
    Drop,
    DropData,
    ImageLabel,
    TextLabel,
)

from rovr import RESOURCE_PACKAGE, get_console
from rovr.classes.textual_validators import (
    AllowsExistingFiles,
    IsValidFilePath,
)
from rovr.classes.type_aliases import KeyBinding, KeyMap
from rovr.core import (
    PinnedSidebar,
    PinnedSidebarContainer,
)
from rovr.footer import ProcessContainer
from rovr.functions import drag_image, icons
from rovr.functions import pins as pin_utils
from rovr.functions.cwd import getcwd
from rovr.functions.path import (
    decompress,
    normalise,
    samefile,
)
from rovr.functions.themes import (
    extract_variable_declarations,
    pop_theme_field_overrides,
    register_all_themes,
    resolve_theme_ansi,
    resolve_variable_references,
    theme_file_mtimes,
)
from rovr.functions.utils import (
    s,
)
from rovr.header.tabs import TablineTab
from rovr.navigation_widgets import (
    UpButton,
)
from rovr.screens import ModalInput, PasteDropScreen
from rovr.variables.constants import config
from rovr.variables.maps import RovrVars

console = get_console


class ThemeHandler:
    # higher index = higher priority
    CSS_PATH = [(resources.files(RESOURCE_PACKAGE)) / "style.tcss"] + (
        [path.join(RovrVars.ROVRCONFIG, "style.tcss")]
        if path.exists(path.join(RovrVars.ROVRCONFIG, "style.tcss"))
        else []
    )
    # the stylesheet source holding the active theme's css rules
    THEME_CSS_SOURCE: ClassVar[tuple[str, str]] = ("<active theme>", "")

    def action_change_theme(self: App) -> None:
        from rovr.screens import ThemeChooser

        original_theme = self.theme

        def apply_theme(result: str | None) -> None:
            self.theme = (
                result if result and result in self.available_themes else original_theme
            )

        self.push_screen(ThemeChooser(), callback=apply_theme)

    def _watch_theme(self: App, theme_name: str) -> None:
        theme = self.get_theme(theme_name)
        self.ansi_color = (
            resolve_theme_ansi(theme, config["theme"]["transparent"])[0]
            if theme is not None
            else config["theme"]["transparent"]
        )
        self._load_theme_css()
        # no i cannot use `super()` because super() would resolve to
        # super of App, which doesn't make sense, so ty cries
        App._watch_theme(self, theme_name)

    def _load_theme_css(self: App) -> None:
        """
        Swap the active theme's css rules into the stylesheet.

        Only the active theme's rules are ever loaded (as the single
        `THEME_CSS_SOURCE` source), so theme files don't need to scope their
        selectors. The swap happens before `refresh_css` reparses the
        stylesheet, from `_watch_theme` and `reload_themes`. The tie breaker
        lets a theme rule beat a style.tcss rule of equal specificity, which
        it would otherwise lose to purely on source order.
        """
        css = getattr(self.current_theme, "css", "")
        existing = self.stylesheet.source.get(self.THEME_CSS_SOURCE)
        if existing is not None and existing.content == css:
            return
        trial = self.stylesheet.copy()
        trial.set_variables(self.get_css_variables())
        trial.add_source(css, read_from=self.THEME_CSS_SOURCE, tie_breaker=1)
        try:
            trial.parse()
        except StylesheetParseError as error:
            # str(StylesheetParseError) is just the object repr; the useful
            # detail lives in the (token, message) pairs of each failed rule
            problems = dict.fromkeys(
                problem for rule in error.errors.rules for problem in rule.errors
            )
            details = "\n".join(
                f"line {(token.referenced_by or token).location[0] + 1}: "
                + Text.from_markup(str(getattr(message, "summary", message))).plain
                for token, message in problems
            )
            self.notify(
                f"css rules in the '{self.theme}' theme failed to parse\n{details}",
                title="Theme Error",
                severity="warning",
                markup=False,
            )
            return
        except Exception as error:
            self.notify(
                f"css rules in the '{self.theme}' theme failed to parse: {error}",
                title="Theme Error",
                severity="warning",
                markup=False,
            )
            return
        self.stylesheet.add_source(css, read_from=self.THEME_CSS_SOURCE, tie_breaker=1)

    def reload_themes(self: App) -> list[str]:
        """
        Pick up theme files added or edited since the last check.

        Returns:
            list[str]: human-readable errors for files that failed to parse.
        """
        mtimes = theme_file_mtimes()
        if mtimes == self._theme_file_mtimes:
            return []
        started = perf_counter()
        changed = {
            path.basename(theme_path)
            for theme_path in self._theme_file_mtimes.keys() | mtimes.keys()
            if self._theme_file_mtimes.get(theme_path) != mtimes.get(theme_path)
        }
        self._theme_file_mtimes = mtimes
        active_theme = self.current_theme
        errors = register_all_themes(self)
        # Theme's dataclass __eq__ ignores the injected css attribute, so a
        # rules-only edit needs its own comparison
        if self.current_theme != active_theme or getattr(
            self.current_theme, "css", ""
        ) != getattr(active_theme, "css", ""):
            self._watch_theme(self.theme)
        if not errors:
            elapsed = (perf_counter() - started) * 1000
            what = (
                ", ".join(sorted(changed))
                if len(changed) <= 3
                else f"{len(changed)} theme files"
            )
            self.notify(f"Reloaded {what} in {elapsed:.0f} ms", title="Themes")
        self.query_one(ProcessContainer).watch_theme(self.theme)
        return errors

    def _poll_theme_files(self: App) -> None:
        for error in self.reload_themes():
            self.notify(error, title="Theme Error", severity="warning", markup=False)

    def get_css_variables(self) -> dict[str, str]:
        # RovrStylesheet strips `$name:` declarations from the CSS files, so
        # every source's declarations are resolved here instead: bundled style,
        # active theme, then the user's style.tcss in ascending priority.
        bundled_declarations: dict[str, str] = {}
        custom_declarations: dict[str, str] = {}
        with (
            suppress(OSError),
            open(self.CSS_PATH[0], "rt", encoding="utf-8") as css_file,
        ):
            bundled_declarations = extract_variable_declarations(css_file.read())
        if self.CUSTOM_STYLE_AVAILABLE:
            with (
                suppress(OSError),
                open(
                    path.join(RovrVars.ROVRCONFIG, "style.tcss"),
                    "rt",
                    encoding="utf-8",
                ) as css_file,
            ):
                custom_declarations = extract_variable_declarations(css_file.read())
        # declarations that map onto Theme fields go through the color system,
        # so an overridden $primary regenerates $primary-lighten-3 and friends
        theme = self.current_theme
        pop_theme_field_overrides(bundled_declarations)
        field_overrides = pop_theme_field_overrides(custom_declarations)
        if field_overrides:
            theme = replace(theme, **field_overrides)  # ty: ignore[invalid-argument-type]
        variables = theme.to_color_system().generate()
        variables = {**self.get_theme_variable_defaults(), **variables}
        declared = {**bundled_declarations, **theme.variables, **custom_declarations}
        for field_name in field_overrides:
            declared.pop(field_name.replace("_", "-"), None)
        # Everything else resolves only after all sources are merged, so
        # `$border-focused: $primary-lighten-3;` in the bundled file picks up
        # a theme or user override of either name.
        variables.update(resolve_variable_references(declared, variables))
        self.theme_variables = variables
        return variables

    @work
    async def _toggle_transparency(self: App) -> None:
        self.ansi_color = not self.ansi_color
        self.refresh()
        self.call_after_refresh(self.refresh_css)
        self.file_list.update_border_subtitle()
        config["theme"]["transparent"] = bool(self.ansi_color)

    async def _on_css_change(self) -> None:
        if self.css_monitor is not None:
            css_paths = self.css_monitor._paths
        else:
            css_paths = self.css_path
        if css_paths:
            try:
                time = perf_counter()
                stylesheet = self.stylesheet.copy()
                stylesheet.set_variables(self.get_css_variables())
                try:
                    # textual issue, i don't want to fix the typing
                    stylesheet.read_all(css_paths)  # ty: ignore[invalid-argument-type]
                except StylesheetError as error:
                    # If one of the CSS paths is no longer available (or perhaps temporarily unavailable),
                    #  we'll end up with partial CSS, which is probably confusing more than anything. We opt to do
                    #  nothing here, knowing that we'll retry again very soon, on the next file monitor invocation.
                    #  Related issue: https://github.com/Textualize/textual/issues/3996
                    self._css_has_errors = True
                    if all(path.exists(css_path) for css_path in css_paths):
                        self.notify(
                            str(error),
                            title=f"CSS: {type(error).__name__}",
                            severity="error",
                            markup=False,
                        )
                    else:
                        unable_path = [
                            css_path
                            for css_path in css_paths
                            if not path.exists(css_path)
                        ]
                        if len(unable_path) == 1:
                            self.notify(
                                f"CSS file {unable_path[0]} cannot be found.",
                                title="CSS: File Not Found",
                                severity="warning",
                                markup=False,
                            )
                        else:
                            self.notify(
                                f"CSS files {unable_path} cannot be found.",
                                title="CSS: Files Not Found",
                                severity="warning",
                                markup=False,
                            )
                    return
                stylesheet.parse()
                elapsed = (perf_counter() - time) * 1000
                self.notify(
                    f"Reloaded {len(css_paths)} CSS files in {elapsed:.0f} ms",
                    title="CSS",
                )
            except StylesheetParseError as exc:
                self._css_has_errors = True
                with self.suspend():
                    console().print(exc.errors)
                    try:
                        console().input(" [bright_blue]Continue? [/]")
                    except EOFError:
                        self.exit(return_code=1)
            except Exception as error:
                # TODO: Catch specific exceptions
                self._css_has_errors = True
                self.bell()
                self.notify(
                    str(error),
                    title=f"CSS: {type(error).__name__}",
                    severity="error",
                    markup=False,
                )
            else:
                self._css_has_errors = False
                self.stylesheet = stylesheet
                self.stylesheet.update(self)
                for screen in self.screen_stack:
                    self.stylesheet.update(screen)


class DragAndDrop:
    async def dnd_drag_out_operation(
        self: App, pos: Offset
    ) -> DNDDragOutOperation | None:
        if (pos not in self.file_list.content_region) or (len(self.screen_stack) != 1):
            return

        from pathlib import Path

        if not self.file_list.select_mode:
            await self.file_list._on_click(
                events.Click(
                    widget=self.file_list,
                    x=pos.x,
                    y=pos.y,
                    delta_x=0,
                    delta_y=0,
                    button=1,
                    shift=False,
                    meta=False,
                    ctrl=False,
                    style=self.screen.get_style_at(pos.x, pos.y),
                )
            )

        selected = await self.file_list.get_selected_objects()
        if not selected:
            return None
        else:
            self._mouse_down_widget = (
                None  # necessary so events.Click doesn't get sent to FileList
            )
            self._dnd_dragged_paths = selected
            if len(selected) == 1:
                icon, icon_color = icons.get_icon_smart(selected[0])
                label_text = path.basename(selected[0])
            elif all(path.isdir(p) for p in selected):
                icon, icon_color = icons.get_icon("folder", "default")
                label_text = f"{len(selected)} folder{s(selected)}"
            else:
                # instead of doing a catch-all for files, preferrably we should check whether all items
                # are the same icon, and if so, use the same icon
                icos = {icons.get_icon_smart(p) for p in selected}
                if len(icos) == 1:
                    icon, icon_color = icos.pop()
                else:
                    icon, icon_color = icons.get_icon("file", "default")
                kind = "file" if all(path.isfile(p) for p in selected) else "item"
                label_text = f"{len(selected)} {kind}{s(selected)}"

            label: ImageLabel | TextLabel = await asyncio.to_thread(
                drag_image.render_drag_image,
                icon,
                label_text,
                icon_color,
                self.theme_variables,
                selected[0] if len(selected) == 1 else None,
            ) or TextLabel(
                f" {icon}  {label_text}",
                size=2,
            )

            return DNDDragOutOperation(
                [Path(p).as_uri() for p in selected],
                "either",
                label=label,
                extra_mimes={
                    # this is the most off-spec way to handle this
                    f"rovr/cwd-{getcwd()}": b"look at mime",
                    f"rovr/count-{len(selected)}": b"look at mime",
                    f"rovr/type-{'folder' if all(path.isdir(p) for p in selected) else 'file'}": b"look at mime",
                },
            )

    def _directory_under_pos(self: App, pos: Offset) -> str | None:
        if pos not in self.file_list.content_region:
            return None
        option_index = self.screen.get_style_at(pos.x, pos.y).meta.get("option")
        if (
            isinstance(option_index, int)
            and 0 <= option_index < self.file_list.option_count
        ):
            option = self.file_list.get_option_at_index(option_index)
            dir_entry = getattr(option, "dir_entry", None)
            if dir_entry is not None and dir_entry.is_dir():
                return normalise(dir_entry.path)
        return None

    def _pinned_directory_under_pos(self: App, pos: Offset) -> str | None:
        sidebar = self._pinned_sidebar_container.pinned_sidebar
        if pos not in sidebar.content_region:
            return None
        option_index = self.screen.get_style_at(pos.x, pos.y).meta.get("option")
        if isinstance(option_index, int) and 0 <= option_index < sidebar.option_count:
            option = sidebar.get_option_at_index(option_index)
            if not option.disabled and option.id is not None:
                directory = decompress(option.id.rsplit("-", 1)[0])
                if path.isdir(directory):
                    return normalise(directory)
        return None

    def _drop_destination(self: App, pos: Offset) -> str:
        return self._directory_under_pos(pos) or normalise(getcwd())

    @staticmethod
    def _drop_conflicts(sources: Iterable[str], destination: str) -> bool:
        destination = path.normcase(path.realpath(destination))
        for source in sources:
            source_path = path.normcase(path.realpath(source))
            if path.isdir(source):
                try:
                    if path.commonpath([source_path, destination]) == source_path:
                        return True
                except ValueError:
                    pass
            elif path.dirname(source_path) == destination and samefile(
                getcwd(), destination
            ):
                return True
        return False

    def on_drag_out_finished(self: App, event: DragOutFinished) -> None:
        self._dnd_dragged_paths = []
        if self._dnd_timer:
            self._dnd_timer[0].stop()
            self._dnd_timer = None

    @on(events.AppBlur)
    def watch_state(self: App, state: str = "idle") -> None:
        if state == "idle" and self._dnd_timer:
            self._dnd_timer[0].stop()
            self._dnd_timer = None

    async def dnd_drag_in_operation(self: App, event: DNDDragIn) -> DNDDragInOperation:
        hover_target: TablineTab | UpButton | str | None = None
        pinned_sidebar = self.query_one(PinnedSidebar)
        self._file_list_container.set_class(
            event.pos in self.file_list.content_region, "dnd-hover"
        )
        self.query_one(PinnedSidebarContainer).set_class(
            event.pos in pinned_sidebar.region, "dnd-hover"
        )
        if event.pos in self.tabWidget.region:
            for tab in self.tabWidget.query(TablineTab):
                if event.pos in tab.region:
                    if tab.id != self.tabWidget.active:
                        hover_target = tab
                    break
        elif event.pos in self.file_list.content_region:
            directory = self._directory_under_pos(event.pos)
            if directory != normalise(getcwd()):
                hover_target = directory
        elif event.pos in pinned_sidebar.content_region:
            directory = self._pinned_directory_under_pos(event.pos)
            if directory != normalise(getcwd()):
                hover_target = directory
        else:
            up_button = self.query_one(UpButton)
            if event.pos in up_button.region and not up_button.disabled:
                hover_target = up_button

        if self._dnd_timer and (
            self._dnd_timer[1] != hover_target
            or (
                isinstance(self._dnd_timer[1], str)
                and self._dnd_timer[2].pos != event.pos
            )  # check whether it is in filelist, and if so, whether the pos is same
            # real pos will change if the mouse isnt stable, but pos should be okay
        ):
            self._dnd_timer[0].stop()
            self._dnd_timer = None
        if hover_target is not None and self._dnd_timer is None:

            def open_hover_target(
                target: TablineTab | UpButton | str = hover_target,
            ) -> None:
                if self.state == "idle":
                    self._dnd_timer.cancel()
                    self._dnd_timer = None
                if isinstance(target, TablineTab):
                    self.tabWidget.active = target.id
                elif isinstance(target, UpButton):
                    target.press()
                    self._dnd_timer = (
                        self.set_timer(0.7, open_hover_target),
                        hover_target,
                        event,
                    )
                elif path.isdir(target):
                    self.cd(target)

            self._dnd_timer = (
                self.set_timer(0.7, open_hover_target),
                hover_target,
                event,
            )

        dropping_to_pins = (
            len(self.screen_stack) == 1
            and event.pos in pinned_sidebar.region
            and "rovr/type-folder" in event.mimes
        )
        accepted = dropping_to_pins or (
            event.pos in self.file_list.content_region
            and (
                len(self.screen_stack) == 1 or isinstance(self.screen, PasteDropScreen)
            )
        )
        if accepted and not dropping_to_pins and self.state == "drag-out":
            accepted = not self._drop_conflicts(
                self._dnd_dragged_paths,
                self._drop_destination(event.pos),
            )
        if (
            accepted
            and not dropping_to_pins
            and any(mime.startswith("rovr/cwd-") for mime in event.mimes)
        ):
            # get cwd
            for mime in event.mimes:
                if mime.startswith("rovr/cwd-"):
                    cwd = mime[9:]
                    break
            if samefile(cwd, getcwd()) and self._directory_under_pos(event.pos) is None:
                accepted = False

        return DNDDragInOperation(
            accepted,
            "either",
            ["text/uri-list", "text/plain"],
        )

    async def on_drop(self: App, event: Drop) -> None:
        if self._dnd_timer:
            self._dnd_timer[0].stop()
            self._dnd_timer = None
        if "text/uri-list" in event.mimes:
            idx = event.mimes.index("text/uri-list")
        elif "text/plain" in event.mimes:
            idx = event.mimes.index("text/plain")
        else:
            self.notify(
                f"No supported mime type offered (available: {event.mimes})",
                title="Drop (NotImplemented)",
                severity="warning",
                markup=False,
            )
            return
        drop_to_pins = (
            event.pos in self.query_one(PinnedSidebar).region
            and "rovr/type-folder" in event.mimes
        )
        self._dnd_drop_metadata[event] = (
            self._drop_destination(event.pos),
            drop_to_pins,
        )
        self.request_data(event, idx, close=True)

    @work
    async def on_drop_data(self: App, event: DropData) -> None:
        from pathlib import Path
        from urllib.parse import urlparse

        destination, drop_to_pins = self._dnd_drop_metadata.pop(
            event.drop_event,
            (normalise(getcwd()), False),
        )
        if event.mime == "text/plain":
            event.data = (
                event.data.decode("utf-8", errors="ignore").strip().splitlines()
            )
        elif event.mime != "text/uri-list":
            self.notify(
                f"Unsupported received mime type (possible interception): {event.mime}",
                title="Drop (NotImplemented)",
                severity="warning",
                markup=False,
            )
            return
        if isinstance(event.data, list):
            sdata = set(event.data)
            files = set(uri for uri in event.data if urlparse(uri).scheme == "file")
            online = set(
                uri for uri in event.data if urlparse(uri).scheme in ("http", "https")
            )
            etc = sdata - (files | online)
            etc_schemes = set(urlparse(uri).scheme for uri in etc)
            if files:
                dropped_paths = sorted(Path.from_uri(uri).as_posix() for uri in files)
                if drop_to_pins:
                    available_pins = pin_utils.pins or pin_utils.load_pins()
                    existing_pins = {
                        normalise(pin["path"])
                        for pin in available_pins.get("pins", [])
                        if isinstance(pin, dict) and isinstance(pin.get("path"), str)
                    }
                    added = False
                    for dropped_path in dropped_paths:
                        normalized = normalise(dropped_path)
                        if path.isdir(normalized) and normalized not in existing_pins:
                            pin_utils.add_pin(
                                path.basename(path.normpath(normalized)) or normalized,
                                normalized,
                            )
                            existing_pins.add(normalized)
                            added = True
                    if added:
                        with suppress(OSError):
                            self._pins_mtime = path.getmtime(pin_utils.PIN_PATH)
                        self.query_one(PinnedSidebar).reload_pins()
                    return
                if self._drop_conflicts(dropped_paths, destination):
                    self.notify(
                        "One or more items conflict with the drop destination.",
                        title="Drop Rejected",
                        severity="warning",
                    )
                    return
                await self._show_paste_drop(
                    events.Paste("\n".join(dropped_paths)),
                    destination,
                )
            if etc:
                self.notify(
                    f"Received {len(etc)} URI(s) which aren't supported\n{etc_schemes}",
                    title="DropData (NotImplemented)",
                    severity="warning",
                    markup=False,
                )
            if online:  # noqa: SIM102
                online = sorted(online)
                # check if it is a PasteDropScreen, if so, reject
                if isinstance(self.screen, PasteDropScreen):
                    self.notify(
                        f"Received {len(online)} http(s) URI(s) which aren't supported on this screen",
                        title="DropData (NotImplemented)",
                        severity="warning",
                        markup=False,
                    )
                else:
                    # this is under heavy assumption that you cannot drag multiple http
                    # links, please prove me wrong and open a bug report
                    assert len(online) == 1
                    resp: str | None = await self.push_screen_wait(
                        ModalInput(
                            "Save file as",
                            "existing file will be overwritten",
                            initial_value=path.basename(urlparse(online[0]).path),
                            validators=[IsValidFilePath(), AllowsExistingFiles()],
                            is_path=True,
                        )
                    )
                    if resp:
                        self.query_one(ProcessContainer).remote_download(online, [resp])

    @work
    async def on_paste(self: App, event: events.Paste) -> None:
        from urllib.parse import urlparse

        if len(self.screen_stack) != 1:
            if self._p_timer:
                self._p_timer.stop()
            self._p_timer = self.set_timer(
                0.1,
                lambda: self.notify(
                    "Bracketed Paste will only work in the main screen.",
                    severity="warning",
                ),
            )
            return
        if any(
            urlparse(line).scheme in ("http", "https")
            for line in event.text.splitlines()
        ):
            if len(event.text.splitlines()) > 1:
                self.notify(
                    "Multiple http(s) links are not supported.",
                    title="Paste (NotImplemented)",
                    severity="warning",
                )
                return
            # no multi files, dont want to ask multiple times
            resp: str | None = await self.push_screen_wait(
                ModalInput(
                    "Save file as",
                    "existing file will be overwritten",
                    initial_value=path.basename(urlparse(event.text).path),
                    validators=[IsValidFilePath(), AllowsExistingFiles()],
                    is_path=True,
                )
            )
            if resp:
                self.query_one(ProcessContainer).remote_download([event.text], [resp])
            return

        await self._show_paste_drop(event, normalise(getcwd()))

    async def _show_paste_drop(
        self: App, event: events.Paste, destination: str
    ) -> None:
        response = await self.push_screen_wait(PasteDropScreen(event))
        if response is not None and response.paths:
            process_container = self.query_one(ProcessContainer)
            match response.action:
                case "copy":
                    process_container.paste_items(
                        copied=response.paths, has_cut=[], dest=destination
                    )
                case "move":
                    process_container.paste_items(
                        copied=[], has_cut=response.paths, dest=destination
                    )


class KeyChordPopup(Static):
    def __init__(self) -> None:
        super().__init__(id="key_chord")
        self.display = False

    def show_chord(
        self,
        bindings: KeyMap,
        default_namespace: DOMNode,
        namespaces: dict[str, DOMNode],
    ) -> None:
        columns = (
            1
            if "-filelist-only" in self.screen.classes
            else 2
            if "-no-preview" in self.screen.classes
            else 3
        )
        table = Table.grid(expand=True, padding=(0, 1))
        for _ in range(columns):
            table.add_column(ratio=1)

        cells = []
        for key, binding in bindings.items():
            if key == "desc" or not isinstance(binding, dict):
                continue
            display_key = f"<{key}>" if "+" in key else key
            description = cast(str, binding.get("desc") or binding.get("action") or key)
            action = binding.get("action")
            namespace = (
                namespaces.get(action.partition(".")[0], default_namespace)
                if action is not None
                else default_namespace
            )
            describe = getattr(namespace, "describe_key_chord_action", None)
            if callable(describe) and action is not None:
                description = describe(action, description)
            cells.append(
                Text.assemble(
                    (display_key, "bold"),
                    f"  {description}",
                    overflow="ellipsis",
                    no_wrap=True,
                )
            )
        for index in range(0, len(cells), columns):
            table.add_row(*cells[index : index + columns])

        title = bindings.get("desc")
        self.border_title = title if isinstance(title, str) else "Key chord"
        self.update(table)
        self.display = True

    def hide_chord(self) -> None:
        self.display = False


class KeyHandler:
    _key_chord: KeyMap | None = None
    _key_chord_namespace: DOMNode | None = None
    _key_chord_popup: KeyChordPopup | None = None

    def push_screen(
        self: App,
        screen: Any,
        callback: Any = None,
        wait_for_dismiss: bool = False,
        *,
        mode: str | None = None,
    ) -> Any:
        self._cancel_key_chord()
        return App.push_screen(self, screen, callback, wait_for_dismiss, mode=mode)

    @lru_cache(maxsize=128)
    @staticmethod
    def shorten_key(key: str) -> str:
        from textual.keys import key_to_character

        *modifiers, name = key.split("+")
        character = {
            "slash": "/",
            "backslash": "\\",
            "at": "@",
            "underscore": "_",
            "minus": "-",
            "plus": "+",
        }.get(name) or key_to_character(name)

        if character is not None and character.isprintable() and character != " ":
            name = character

        return "+".join((*modifiers, name))

    async def _check_bindings(self: App, key: str, priority: bool = False) -> bool:
        if not self.keys or self.screen.id == "--command-palette":
            return await App._check_bindings(self, key, priority)
        key = KeyHandler.shorten_key(key)
        namespaces = self._key_namespaces()
        if priority and self._key_chord is not None:
            if key == "escape":
                self._cancel_key_chord()
                return True
            binding = self._key_chord.get(key)
            if isinstance(binding, dict):
                if "action" not in binding:
                    self._key_chord = cast(KeyMap, binding)
                    self._key_chord_popup.show_chord(
                        self._key_chord, self._key_chord_namespace, namespaces
                    )
                    return True
                namespace = self._key_chord_namespace
                action = cast(KeyBinding, binding)["action"]
                self._cancel_key_chord()
                if action == "noop":
                    return True
                return namespace is not None and await self.run_action(
                    action,
                    default_namespace=namespace,
                    namespaces=namespaces,
                )
            self._cancel_key_chord()
            return True

        if (
            priority
            and self.focused is not None
            and self.focused.check_consume_key(key, key)
        ):
            return False

        contexts = [("global", self)] if priority else self._active_key_contexts()
        for context, namespace in contexts:
            context = self.keys.get(context, {})
            binding = context.get(key)
            if not isinstance(binding, dict):
                continue
            if "action" not in binding:
                self._key_chord = cast(KeyMap, binding)
                self._key_chord_namespace = namespace
                self._key_chord_popup = KeyChordPopup()
                await self.screen.mount(self._key_chord_popup)
                self._key_chord_popup.show_chord(self._key_chord, namespace, namespaces)
                return True
            action = cast(KeyBinding, binding)["action"]
            if action == "noop":
                return True
            if action is not None and await self.run_action(
                action,
                default_namespace=namespace,
                namespaces=namespaces,
            ):
                return True
        return False

    def _cancel_key_chord(self: App) -> None:
        self._key_chord = None
        self._key_chord_namespace = None
        if self._key_chord_popup is not None:
            self._key_chord_popup.hide_chord()
            self._key_chord_popup.remove()
            self._key_chord_popup = None

    def _active_key_contexts(self: App) -> list[tuple[str, DOMNode]]:
        contexts: list[tuple[str, DOMNode]] = []
        focused = self.focused
        nodes = focused.ancestors_with_self if focused is not None else [self.screen]
        for node in nodes:
            contexts.extend(
                (context, node) for context in getattr(node, "key_contexts", ())
            )
            if node is self.screen:
                break
        if len(self.screen_stack) == 1:
            contexts.append(("main", self))
        return contexts

    def _key_namespaces(self: App) -> dict[str, DOMNode]:
        namespaces: dict[str, DOMNode] = {"app": self, "screen": self.screen}
        for node in self.screen.walk_children(with_self=True):
            contexts = getattr(node, "key_contexts", ())
            if contexts:
                namespaces.setdefault(contexts[0], node)

        if self.focused is not None:
            for node in reversed(self.focused.ancestors_with_self):
                contexts = getattr(node, "key_contexts", ())
                if contexts:
                    namespaces[contexts[0]] = node
        return namespaces
