from dataclasses import dataclass, field
from os import path
from pathlib import PurePath

from textual.css.stylesheet import Stylesheet
from textual.theme import Theme

from .config import _RovrConfigCustomThemeItemBarGradient


@dataclass
class RovrThemeClass(Theme):
    name: str
    primary: str
    secondary: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    foreground: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    boost: str | None = None
    dark: bool = True
    luminosity_spread: float = 0.15
    text_alpha: float = 0.95
    variables: dict[str, str] = field(default_factory=dict)
    bar_gradient: _RovrConfigCustomThemeItemBarGradient | None = None


class RovrStylesheet(Stylesheet):
    """Stylesheet that strips top-level `$variable:` declarations from the CSS
    files it reads.

    Those declarations are resolved app-wide by `Application.get_css_variables`
    instead; if Textual parsed them a second time it would append their tokens
    onto the injected value (variable redefinition concatenates rather than
    replaces), corrupting every `$variable` reference.
    """

    def read(self, filename: str | PurePath) -> None:
        from rovr.functions.themes import strip_variable_declarations

        super().read(filename)
        # same key computation as Stylesheet.read
        key = (path.abspath(path.expanduser(str(filename))), "")
        source = self.source[key]
        self.source[key] = source._replace(
            content=strip_variable_declarations(source.content)
        )

    def copy(self) -> "RovrStylesheet":
        stylesheet = RovrStylesheet(variables=self._variables.copy())
        stylesheet.source = self.source.copy()
        return stylesheet
