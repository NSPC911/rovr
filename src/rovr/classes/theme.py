from os import path
from pathlib import PurePath

from textual.css.styles import RulesMap
from textual.css.stylesheet import Stylesheet
from textual.dom import DOMNode


class RovrStylesheet(Stylesheet):
    """Stylesheet that strips top-level `$variable:` declarations from the CSS
    files it reads.

    Those declarations are resolved app-wide by `Application.get_css_variables`
    instead; if Textual parsed them a second time it would append their tokens
    onto the injected value (variable redefinition concatenates rather than
    replaces), corrupting every `$variable` reference.
    """

    has_applied: bool = False

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

    def apply(
        self,
        node: DOMNode,
        *,
        animate: bool = False,
        cache: dict[tuple, RulesMap] | None = None,
    ) -> None:
        if not self.has_applied:
            self.has_applied = True
        else:
            return super().apply(node, animate=animate, cache=cache)
