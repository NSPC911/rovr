# modal tester, use when necessary
from importlib import resources
from time import perf_counter
from typing import Iterable

from rich.console import Console
from textual import on
from textual.app import App, ComposeResult, SystemCommand
from textual.css.errors import StylesheetError
from textual.css.stylesheet import StylesheetParseError
from textual.screen import Screen
from textual.widgets import Button

from rovr.functions.cwd import getcwd
from rovr.screens import (
    ArchiveCreationScreen,
    DeleteFiles,
    Dismissible,
    FileInUse,
    FileNameConflict,
    YesOrNo,
)

console = Console()

# these are screens that are more risky test in the normal app


class Test(App):
    CSS_PATH = resources.files("rovr") / "style.tcss"

    HORIZONTAL_BREAKPOINTS = [
        (0, "-filelist-only"),
        (35, "-no-preview"),
        (70, "-all-horizontal"),
    ]
    VERTICAL_BREAKPOINTS = [
        (0, "-middle-only"),
        (16, "-no-menu-at-all"),
        (19, "-no-path"),
        (24, "-all-vertical"),
    ]

    def __init__(self) -> None:
        super().__init__(watch_css=True)

    def compose(self) -> ComposeResult:
        yield Button("Delete Files", id="DeleteFiles")
        yield Button("Dismissible", id="Dismissible")
        yield Button("File In Use", id="FileInUse")
        yield Button("File Name Conflict", id="FileNameConflict")
        yield Button("Paste Screen", id="PasteScreen")
        yield Button("Yes Or No", id="YesOrNo")

    @on(Button.Pressed, "#FileNameConflict")
    def common_file_name_do_what(self) -> None:
        self.push_screen(
            FileNameConflict(
                "Path already exists in destination\nWhat do you want to do now?",
                border_title="test.txt",
                border_subtitle=f"Extracting to {getcwd()}",
            ),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    @on(Button.Pressed, "#DeleteFiles")
    def delete_files(self) -> None:
        self.push_screen(
            DeleteFiles(
                "Are you sure you want to delete the following files?",
                ["file1.txt", "file2.txt", "file3.txt"],
            ),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    @on(Button.Pressed, "#Dismissible")
    def dismissable(self) -> None:
        self.push_screen(
            Dismissible("This is a dismissable screen. Press any key to dismiss."),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    @on(Button.Pressed, "#FileInUse")
    def file_in_use(self) -> None:
        self.push_screen(
            FileInUse(
                "The file 'example.txt' is currently in use by another application.\nexample.txt",
            ),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    @on(Button.Pressed, "#YesOrNo")
    def yes_or_no(self) -> None:
        self.push_screen(
            YesOrNo("Do you want to continue?"),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    @on(Button.Pressed, "#ArchiveCreationScreen")
    def archive_creation_screen(self) -> None:
        self.push_screen(
            ArchiveCreationScreen(
                initial_value="archive.zip",
                is_path=True,
            ),
            callback=lambda result: self.notify(str(result), markup=False),
        )

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        if not self.ansi_color:
            yield SystemCommand(
                "Change theme",
                "Change the current theme",
                self.action_change_theme,
            )
        yield SystemCommand(
            "Quit the application",
            "Quit the application as soon as possible",
            self.action_quit,
        )

        if screen.maximized is not None:
            yield SystemCommand(
                "Minimize",
                "Minimize the widget and restore to normal size",
                screen.action_minimize,
            )
        elif screen.focused is not None and screen.focused.allow_maximize:
            yield SystemCommand(
                "Maximize", "Maximize the focused widget", screen.action_maximize
            )

        yield SystemCommand(
            "Save screenshot",
            "Save an SVG 'screenshot' of the current screen",
            lambda: self.set_timer(0.1, self.deliver_screenshot),
        )

        if self.ansi_color:
            yield SystemCommand(
                "Disable Transparent Theme",
                "Go back to an opaque background.",
                lambda: self.call_later(self._toggle_transparency),
            )
        else:
            yield SystemCommand(
                "Enable Transparent Theme",
                "Have a transparent background.",
                lambda: self.call_later(self._toggle_transparency),
            )

    async def _on_css_change(self) -> None:
        if self.css_monitor is not None:
            css_paths = self.css_monitor._paths
        else:
            css_paths = self.css_path
        if css_paths:
            try:
                time = perf_counter()
                stylesheet = self.stylesheet.copy()
                try:
                    # textual issue, i don't want to fix the typing
                    stylesheet.read_all(css_paths)  # ty: ignore[invalid-argument-type]
                except StylesheetError as error:
                    # If one of the CSS paths is no longer available (or perhaps temporarily unavailable),
                    #  we'll end up with partial CSS, which is probably confusing more than anything. We opt to do
                    #  nothing here, knowing that we'll retry again very soon, on the next file monitor invocation.
                    #  Related issue: https://github.com/Textualize/textual/issues/3996
                    self._css_has_errors = True
                    self.notify(
                        str(error),
                        title=f"CSS: {type(error).__name__}",
                        severity="error",
                        markup=False,
                        timeout=5,
                    )
                    return
                stylesheet.parse()
                elapsed = (perf_counter() - time) * 1000
                self.notify(
                    f"Reloaded {len(css_paths)} CSS files in {elapsed:.0f} ms",
                    title="CSS",
                    timeout=2,
                )
            except StylesheetParseError as exc:
                self._css_has_errors = True
                with self.suspend():
                    console.print(exc.errors)
                    try:
                        console.input(" [bright_blue]Continue? [/]")
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

    async def _toggle_transparency(self) -> None:
        self.ansi_color = not self.ansi_color
        self.refresh()
        self.refresh_css()


Test().run()
