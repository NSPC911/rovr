# modal tester, use when necessary
from textual.app import App, ComposeResult
from textual.widgets import Button

from rovr.screens.paste_screen import PasteScreen


class Test(App):
    CSS_PATH = "../style.tcss"

    def compose(self) -> ComposeResult:
        yield Button("hi")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.push_screen(
            PasteScreen(
                "Yo imma do some stuff with these files rq",
                {
                    "copy": ["/path/to/file1", "/path/to/file2"],
                    "cut": ["/path/to/file3"],
                },
            ),
            lambda x: self.notify(str(x)),
        )


Test(watch_css=True).run()
