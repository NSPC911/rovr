import shutil
from contextlib import suppress
from os import chdir, getcwd, path
from types import SimpleNamespace

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    HorizontalGroup,
    HorizontalScroll,
    Vertical,
    VerticalGroup,
)
from textual.css.query import NoMatches
from textual.widgets import Input

from rovr import utils
from rovr.action_buttons import (
    CopyButton,
    CutButton,
    DeleteButton,
    NewItemButton,
    PasteButton,
    RenameItemButton,
    UnzipButton,
    ZipButton,
)
from rovr.core import (
    FileList,
    PinnedSidebar,
    PreviewContainer,
)
from rovr.footer import Clipboard, MetadataContainer, ProcessContainer
from rovr.header import HeaderArea
from rovr.maps import VAR_TO_DIR
from rovr.navigation_widgets import (
    BackButton,
    ForwardButton,
    PathAutoCompleteInput,
    PathInput,
    RefreshButton,
    UpButton,
)
from rovr.screens import YesOrNo, ZDToDirectory
from rovr.search_container import SearchInput
from rovr.themes import get_custom_themes
from rovr.utils import config


class Application(App, inherit_bindings=False):
    # dont need ctrl+c
    BINDINGS = [
        Binding(
            "ctrl+q",
            "quit",
            "Quit",
            tooltip="Quit the app and return to the command prompt.",
            show=False,
            priority=True,
        )
    ]
    # higher index = higher priority
    CSS_PATH = ["style.tcss", path.join(VAR_TO_DIR["CONFIG"], "style.tcss")]
    # reactivity
    HORIZONTAL_BREAKPOINTS = [(0, "-filelistonly"), (60, "-nopreview"), (90, "-all")]
    # VERTICAL_BREAKPOINTS = [(0, "-footerless"), ()]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.prev_selected_option = None
        self.app_blurred = False

    def compose(self) -> ComposeResult:
        print("Starting Rovr...")
        with Vertical(id="root"):
            yield HeaderArea(id="headerArea")
            with HorizontalScroll(id="menu"):
                yield CopyButton()
                yield CutButton()
                yield PasteButton()
                yield NewItemButton()
                yield RenameItemButton()
                yield DeleteButton()
                yield ZipButton()
                yield UnzipButton()
            with VerticalGroup(id="below_menu"):
                with HorizontalGroup():
                    yield BackButton()
                    yield ForwardButton()
                    yield UpButton()
                    yield RefreshButton()
                    path_switcher = PathInput()
                    yield path_switcher
                yield PathAutoCompleteInput(
                    target=path_switcher,
                )
            with HorizontalGroup(id="main"):
                with VerticalGroup(id="pinned_sidebar_container"):
                    yield SearchInput(
                        placeholder=f"({utils.get_icon('general', 'search')[0]}) Search"
                    )
                    yield PinnedSidebar(id="pinned_sidebar")
                with VerticalGroup(id="file_list_container"):
                    yield SearchInput(
                        placeholder=f"({utils.get_icon('general', 'search')[0]}) Search something..."
                    )
                    yield FileList(
                        id="file_list",
                        name="File List",
                        classes="file-list",
                    )
                yield PreviewContainer(
                    id="preview_sidebar",
                )
            with HorizontalGroup(id="footer"):
                # ? should we switch to a vertical scroll for richlog?
                yield ProcessContainer()
                yield MetadataContainer(id="metadata")
                yield Clipboard(id="clipboard")

    def on_mount(self) -> None:
        # this will stay until a beta release.
        def warning(response: bool) -> None:
            match response:
                case True:
                    pass
                case False:
                    self.app.exit(message="Bye! Hope to see you soon!")

        self.push_screen(
            YesOrNo(
                "This is a pre-alpha application.\nUse at your own risk.\nContinue?",
                reverse_color=True,
            ),
            warning,
        )
        # border titles
        self.query_one("#menu").border_title = "Options"
        self.query_one("#below_menu").border_title = "Directory Actions"
        self.query_one("#pinned_sidebar_container").border_title = "Sidebar"
        self.query_one("#file_list_container").border_title = "Files"
        self.query_one("#processes").border_title = "Processes"
        self.query_one("#metadata").border_title = "Metadata"
        self.query_one("#clipboard").border_title = "Clipboard"
        # themes
        for theme in get_custom_themes():
            self.register_theme(theme)
        self.theme = config["theme"]["default"]
        # tooltips
        if config["interface"]["tooltips"]:
            self.query_one("#back").tooltip = "Go back in history"
            self.query_one("#forward").tooltip = "Go forward in history"
            self.query_one("#up").tooltip = "Go up the directory tree"
            self.query_one("#refresh").tooltip = "Refresh the file list"
        self.tabWidget = self.query_one("Tabline")
        # make the file list
        self.query_one("#file_list").update_file_list()
        self.query_one("#file_list").focus()

    def action_focus_next(self) -> None:
        if config["settings"]["allow_tab_nav"]:
            super().action_focus_next()
        else:
            return

    def action_focus_previous(self) -> None:
        if config["settings"]["allow_tab_nav"]:
            super().action_focus_previous()
        else:
            return

    async def on_key(self, event: events.Key) -> None:
        # Not really sure why this can happen, but I will still handle this
        if self.focused is None or not self.focused.id:
            return
        # Make sure that key binds don't break
        match event.key:
            # after input
            case "enter" | "escape" if self.focused.id == "path_switcher":
                await self.query_one(PathInput).action_submit()
                self.query_one("#file_list").focus()
                return
            # placeholder, not yet existing
            case "escape" if "search" in self.focused.id:
                match self.focused.id:
                    case "search_file_list":
                        self.query_one("#file_list").focus()
                    case "search_pinned_sidebar":
                        self.query_one("#pinned_sidebar").focus()
                return
            # backspace is used by default bindings to head up in history
            # so just avoid it
            case "backspace" if (
                type(self.focused) is Input or "search" in self.focused.id
            ):
                return
            # focus toggle pinned sidebar
            case key if key in config["keybinds"]["focus_toggle_pinned_sidebar"]:
                if (
                    self.focused.id == "pinned_sidebar"
                    or "hide" in self.query_one("#pinned_sidebar_container").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one("#pinned_sidebar_container").display:
                    self.query_one("#pinned_sidebar").focus()
            # Focus file list from anywhere except input
            case key if key in config["keybinds"]["focus_file_list"]:
                self.query_one("#file_list").focus()
            # Focus toggle preview sidebar
            case key if key in config["keybinds"]["focus_toggle_preview_sidebar"]:
                if (
                    self.focused.id == "preview_sidebar"
                    or self.focused.parent.id == "preview_sidebar"
                    or "hide" in self.query_one("#preview_sidebar").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one(PreviewContainer).display:
                    with suppress(NoMatches):
                        self.query_one("PreviewContainer > *").focus()
                else:
                    self.query_one("#file_list").focus()
            # Focus path switcher
            case key if key in config["keybinds"]["focus_toggle_path_switcher"]:
                self.query_one("#path_switcher").focus()
            # Focus processes
            case key if key in config["keybinds"]["focus_toggle_processes"]:
                if (
                    self.focused.id == "processes"
                    or "hide" in self.query_one("#processes").classes
                ):
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#processes").focus()
            # Focus metadata
            case key if key in config["keybinds"]["focus_toggle_metadata"]:
                if self.focused.id == "metadata":
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#metadata").focus()
            # Focus clipboard
            case key if key in config["keybinds"]["focus_toggle_clipboard"]:
                if self.focused.id == "clipboard":
                    self.query_one("#file_list").focus()
                elif self.query_one("#footer").display:
                    self.query_one("#clipboard").focus()
            # Toggle hiding panels
            case key if key in config["keybinds"]["toggle_pinned_sidebar"]:
                self.query_one("#file_list").focus()
                if self.query_one("#pinned_sidebar_container").display:
                    self.query_one("#pinned_sidebar_container").add_class("hide")
                else:
                    self.query_one("#pinned_sidebar_container").remove_class("hide")
            case key if key in config["keybinds"]["toggle_preview_sidebar"]:
                self.query_one("#file_list").focus()
                if self.query_one(PreviewContainer).display:
                    self.query_one(PreviewContainer).add_class("hide")
                else:
                    self.query_one(PreviewContainer).remove_class("hide")
            case key if key in config["keybinds"]["toggle_footer"]:
                self.query_one("#file_list").focus()
                if self.query_one("#footer").display:
                    self.query_one("#footer").add_class("hide")
                else:
                    self.query_one("#footer").remove_class("hide")
            case key if (
                key in config["keybinds"]["tab_next"]
                and self.tabWidget.active_tab is not None
            ):
                self.tabWidget.action_next_tab()
            case key if (
                self.tabWidget.active_tab is not None
                and key in config["keybinds"]["tab_previous"]
            ):
                self.tabWidget.action_previous_tab()
            case key if key in config["keybinds"]["tab_new"]:
                await self.tabWidget.add_tab(after=self.tabWidget.active_tab)
            case key if (
                self.tabWidget.tab_count > 1 and key in config["keybinds"]["tab_close"]
            ):
                await self.tabWidget.remove_tab(self.tabWidget.active_tab)
            # zoxide
            case key if (
                config["plugins"]["zoxide"]["enabled"]
                and event.key in config["plugins"]["zoxide"]["keybinds"]
            ):
                if shutil.which("zoxide") is None:
                    self.notify(
                        "Zoxide is not installed or not in PATH.",
                        title="Zoxide",
                        severity="error",
                    )

                def on_response(response: str) -> None:
                    """Handle the response from the ZDToDirectory dialog."""
                    if response:
                        pathinput = self.query_one(PathInput)
                        pathinput.value = utils.decompress(response).replace(
                            path.sep, "/"
                        )
                        pathinput.on_input_submitted(
                            SimpleNamespace(value=pathinput.value)
                        )

                self.push_screen(ZDToDirectory(), on_response)
            # zen mode
            case key if (
                config["plugins"]["zen_mode"]["enabled"]
                and key in config["plugins"]["zen_mode"]["keybinds"]
            ):
                if "zen" in self.classes:
                    self.remove_class("zen")
                else:
                    self.add_class("zen")

    def on_app_blur(self, event: events.AppBlur) -> None:
        self.app_blurred = True

    def on_app_focus(self, event: events.AppFocus) -> None:
        self.app_blurred = False

    @work
    async def action_quit(self) -> None:
        process_container = self.query_one(ProcessContainer)
        if len(process_container.query("ProgressBarContainer")) != len(
            process_container.query(".done") + len(process_container.query(".error"))
        ) and not await self.push_screen_wait(
            YesOrNo(
                f"{len(process_container.query('ProgressBarContainer')) - len(process_container.query('.done')) - len(process_container.query('.error'))}"
                + " processes are still running!\nAre you sure you want to quit?",
                border_title="Quit [teal]rovr[/teal]",
            )
        ):
            return
        self.exit()

    def cd(
        self,
        directory: str,
        add_to_history: bool = True,
        focus_on: str | None = None,
    ) -> None:
        if path.exists(directory):
            if utils.normalise(getcwd()) == utils.normalise(directory):
                self.query_one("#file_list").update_file_list(
                    add_to_session=False, focus_on=focus_on
                )
                return
            else:
                chdir(directory)
                self.query_one("#file_list").update_file_list(
                    add_to_session=add_to_history, focus_on=focus_on
                )
        else:
            while not path.exists(directory):
                directory = "/".join(utils.normalise(directory).split("/")[:-1])
            chdir(directory)
            self.query_one("#file_list").update_file_list(
                add_to_session=add_to_history, focus_on=focus_on
            )


app = Application(watch_css=True)
