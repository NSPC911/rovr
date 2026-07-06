from contextlib import suppress

from textual import on, work
from textual.app import ComposeResult, InvalidThemeError
from textual.containers import VerticalGroup
from textual.style import Style
from textual.widgets import Input, OptionList
from textual_autocomplete.fuzzy_search import Matcher

from rovr.classes.textual_options import OptionWithValue
from rovr.components import ModalSearchScreen
from rovr.components.special_option_lists import DoubleClickableOptionList
from rovr.functions.themes import register_all_themes


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
        # pick up theme files added or edited since startup
        theme_rules, errors = register_all_themes(self.app)
        self.app._theme_rules = theme_rules
        for error in errors:
            self.app.notify(
                error, title="Theme Error", severity="warning", markup=False
            )
        self.themes: list[OptionWithValue] = [
            OptionWithValue(lambda: (" ", ""), name, name)
            for name in sorted(self.app.available_themes)
        ]
        self.post_message(Input.Changed(self.search_input, self.search_input.value))

    @on(OptionList.OptionHighlighted)
    def preview_theme(self, event: OptionList.OptionHighlighted) -> None:
        option = event.option
        if (
            isinstance(option, OptionWithValue)
            and isinstance(option.value, str)
            and not option.disabled
        ):
            with suppress(InvalidThemeError):
                self.app.theme = option.value

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
