from os import getcwd, path

from textual.widgets import Button

from rovr.utils import get_icon


class BackButton(Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(get_icon("general", "left")[0], id="back", *args, **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go back in the sesison's history"""
        state = self.app.tabWidget.active_tab.session
        if state.sessionHistoryIndex != 0:
            state.sessionHistoryIndex -= 1
        # ! reminder to add a check for path!
        self.app.cd(
            state.sessionDirectories[state.sessionHistoryIndex]["path"],
            add_to_history=False,
        )


class ForwardButton(Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(get_icon("general", "right")[0], id="forward", *args, **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go forward in the session's history"""
        state = self.app.tabWidget.active_tab.session
        state.sessionHistoryIndex += 1
        # ! reminder to add a check for path!
        self.app.cd(
            state.sessionDirectories[state.sessionHistoryIndex]["path"],
            add_to_history=False,
        )


class UpButton(Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(get_icon("general", "up")[0], id="up", *args, **kwargs)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Go up the current location's directory"""
        parent = getcwd().split(path.sep)[-1]
        self.app.cd(
            path.sep.join(getcwd().split(path.sep)[:-1]) + path.sep, focus_on=parent
        )
