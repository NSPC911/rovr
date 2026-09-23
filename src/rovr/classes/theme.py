from os import path
from pathlib import PurePath

from textual.css.stylesheet import Stylesheet


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
