import shutil
from importlib import resources
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import VerticalGroup
from textual.style import Style
from textual.widgets import Input
from textual_autocomplete.fuzzy_search import Matcher

from rovr.classes.textual_options import OptionWithValue
from rovr.components import ModalSearchScreen
from rovr.components.special_option_lists import DoubleClickableOptionList
from rovr.variables.maps import RovrVars

default_themes_path = (
    resources.files("_rovr.config")
    if globals().get("__compiled__")
    else resources.files("rovr.config")
) / "themes"
custom_theme_path: Path = Path(RovrVars.ROVRTHEMES)


class ThemeChooser(ModalSearchScreen):
    def compose(self) -> ComposeResult:
        with VerticalGroup(id="theme_chooser_group"):
            yield Input(
                placeholder="Type to filter themes...",
                id="theme_chooser_input",
            )
            yield DoubleClickableOptionList(
                OptionWithValue(None, "Getting themes...", None, disabled=True),
                id="theme_chooser_options",
                classes="empty",
            )

    @work(thread=True)
    def on_mount(self) -> None:
        self.call_later(
            lambda: setattr(self.search_input, "border_title", "Select a theme")
        )
        # ensure up-to-date
        if not custom_theme_path.exists():
            custom_theme_path.mkdir(parents=True, exist_ok=True)
        if default_themes_path.exists():
            for theme in default_themes_path.iterdir():
                if not (custom_theme_path / theme.name).exists(follow_symlinks=True):
                    # move it there
                    shutil.copy(theme, custom_theme_path / theme.name)
        # now get theme names
        self.themes: list[OptionWithValue] = sorted(
            [
                OptionWithValue(lambda: (" ", ""), theme.stem, theme.as_posix())
                for theme in custom_theme_path.iterdir()
                if theme.is_file() and theme.suffix == ".tcss"
            ],
            key=lambda option: option.value,
        )
        self.post_message(Input.Changed(self.search_input, self.search_input.value))

    def on_input_changed(self, event: Input.Changed) -> None:
        if not event.value:
            for opt in self.themes:
                opt._set_prompt(opt.label)
            self.search_options.set_options(self.themes)
            self.search_options.remove_class("empty")
            self.search_options.highlighted = 0
            return
        matcher = Matcher(event.value, match_style=Style(underline=True, bold=True))
        options: list[OptionWithValue] = []
        for theme in self.themes:
            if matcher.match(theme.label) > 0:
                theme._set_prompt(matcher.highlight(theme.label))
                options.append(theme)
        if len(options) == 0:
            self.search_options.set_options([
                OptionWithValue(
                    None,
                    " No themes found",
                    None,
                    disabled=True,
                )
            ])
            self.search_options.add_class("empty")
            return
        self.search_options.set_options(options)
        self.search_options.remove_class("empty")
        self.search_options.highlighted = 0
