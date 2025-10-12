# modal tester, use when necessary
from textual.app import App, ComposeResult
from textual.widgets import Button

from rovr.screens import FileInUse


class Test(App):
    CSS_PATH = "../style.tcss"

    def compose(self) -> ComposeResult:
        yield Button("hi")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.push_screen(
            FileInUse(
                "The file appears to be open in another application and cannot be deleted.\nPath: file.txt",
            ),
            lambda x: self.notify(str(x)),
        )


Test().run()
