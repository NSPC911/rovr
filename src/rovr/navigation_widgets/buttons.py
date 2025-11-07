from os import getcwd, path

from textual.widgets import Button

from rovr.functions.icons import get_icon


class BackButton(Button):
    def __init__(self) -> None:
        super().__init__(get_icon("general", "left")[0], id="back", classes="option")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go back in the sesison's history"""
        if self.disabled:
            return
        state = self.app.tabWidget.active_tab.session
        if state.historyIndex != 0:
            state.historyIndex -= 1
        # ! reminder to add a check for path!
        self.app.cd(
            state.directories[state.historyIndex],
            add_to_history=False,
        )


class ForwardButton(Button):
    def __init__(self) -> None:
        super().__init__(
            get_icon("general", "right")[0], id="forward", classes="option"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go forward in the session's history"""
        if self.disabled:
            return
        state = self.app.tabWidget.active_tab.session
        state.historyIndex += 1
        # ! reminder to add a check for path!
        self.app.cd(
            state.directories[state.historyIndex],
            add_to_history=False,
        )


class UpButton(Button):
    def __init__(self) -> None:
        super().__init__(get_icon("general", "up")[0], id="up", classes="option")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go up the current location's directory"""
        if self.disabled:
            return
        parent = getcwd().split(path.sep)[-1]
        self.app.cd(
            path.sep.join(getcwd().split(path.sep)[:-1]) + path.sep, focus_on=parent
        )
