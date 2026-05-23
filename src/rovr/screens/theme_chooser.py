import shutil
from importlib import resources
from pathlib import Path

from textual import work
from textual.widgets import Input
from textual_autocomplete.fuzzy_search import Matcher

from rovr.components import ModalSearchScreen
from rovr.variables.maps import RovrVars

default_themes_path = (
    resources.files("_rovr.config")
    if globals().get("__compiled__")
    else resources.files("rovr.config")
) / "themes"
custom_theme_path: Path = Path(RovrVars.ROVRCONFIG) / "themes"


def extract_var(var: str, css: str) -> str | None:
    import re

    variable_pattern = re.compile(
        r"(?m)^[ \t]*\$(?P<name>[A-Za-z_][\w-]*)[ \t]*:[ \t]*(?P<value>[^;\n]+)\s*;"
    )

    def scrub_css(source: str) -> str:
        in_block_comment = False
        in_line_comment = False
        in_single_quote = False
        in_double_quote = False
        brace_depth = 0
        output: list[str] = []
        index = 0

        while index < len(source):
            current = source[index]
            next_char = source[index + 1] if index + 1 < len(source) else ""

            if in_line_comment:
                if current == "\n":
                    in_line_comment = False
                    if brace_depth == 0:
                        output.append(current)
                index += 1
                continue

            if in_block_comment:
                if current == "*" and next_char == "/":
                    in_block_comment = False
                    index += 2
                else:
                    index += 1
                continue

            if not in_single_quote and not in_double_quote:
                if current == "/" and next_char == "/":
                    in_line_comment = True
                    index += 2
                    continue
                if current == "/" and next_char == "*":
                    in_block_comment = True
                    index += 2
                    continue

            if current == "\\" and (in_single_quote or in_double_quote):
                if brace_depth == 0:
                    output.append(current)
                if index + 1 < len(source):
                    if brace_depth == 0:
                        output.append(source[index + 1])
                    index += 2
                else:
                    index += 1
                continue

            if not in_double_quote and current == "'":
                in_single_quote = not in_single_quote
                if brace_depth == 0:
                    output.append(current)
                index += 1
                continue

            if not in_single_quote and current == '"':
                in_double_quote = not in_double_quote
                if brace_depth == 0:
                    output.append(current)
                index += 1
                continue

            if not in_single_quote and not in_double_quote:
                if current == "{":
                    brace_depth += 1
                    index += 1
                    continue
                if current == "}" and brace_depth > 0:
                    brace_depth -= 1
                    index += 1
                    continue

            if brace_depth == 0:
                output.append(current)

            index += 1

        return "".join(output)

    stripped_css = scrub_css(css)
    for match in variable_pattern.finditer(stripped_css):
        if match.group("name") == var:
            return match.group("value").strip()
    return None


class ThemeChooser(ModalSearchScreen):
    @work(thread=True)
    def on_mount(self) -> None:
        # ensure up-to-date
        if default_themes_path.exists():
            for theme in default_themes_path.iterdir():
                if not (custom_theme_path / theme.name).lexists():
                    # move it there
                    shutil.copy(theme, custom_theme_path / theme.name)
        # now get theme names
        self.themes = sorted([
            theme
            for theme in custom_theme_path.iterdir()
            if theme.is_file() and theme.suffix == ".tcss"
        ])

    def on_input_changed(self, event: Input.Changed) -> None:
        matcher = Matcher(event.value)
        for theme in self.themes:
            if matcher.match(theme.name) > 0:
                ...
