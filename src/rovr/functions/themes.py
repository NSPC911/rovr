import re

from textual.color import Color

from rovr.classes.theme import RovrThemeClass
from rovr.variables.constants import config

_VARIABLE_DECLARATION = re.compile(r"^\$([\w-]+)\s*:\s*(.+?)\s*;\s*$")
_VARIABLE_REF = re.compile(r"\$[\w-]+")


def get_custom_themes() -> list:
    """
    Get the custom themes defined in the config file.

    Returns:
        list: A list of custom themes.
    """
    custom_themes = []
    for theme in config["custom_theme"]:
        if bar_gradient := theme.get("bar_gradient"):
            if "default" in bar_gradient["default"]:
                for color in bar_gradient["default"]:
                    Color.parse(color)
            if "error" in bar_gradient["error"]:
                for color in bar_gradient["error"]:
                    Color.parse(color)
        custom_themes.append(
            RovrThemeClass(
                bar_gradient=theme.get("bar_gradient", {}),
                name=theme["name"]
                .lower()
                .replace(" ", "-"),  # Keep it similar to default textual behaviour
                primary=theme["primary"],
                secondary=theme["secondary"],
                accent=theme["accent"],
                foreground=theme["foreground"],
                background=theme["background"],
                success=theme["success"],
                warning=theme["warning"],
                error=theme["error"],
                surface=theme["surface"],
                panel=theme["panel"],
                dark=theme["is_dark"],
                variables=theme.get("variables", {}),
            )
        )
    return custom_themes


def extract_variable_overrides(
    css_text: str, resolved: dict[str, str]
) -> dict[str, str]:
    """
    Extract top-level `$name: value;` declarations from a TCSS source, resolving
    any `$other` references against already-known variables as they're encountered.

    Textual only shares `$variables` within the single source they're declared in,
    so a user's style.tcss can't override a variable used by the bundled style.tcss
    just by being loaded as a second CSS source. Folding the user's declarations into
    the app-wide `get_css_variables()` mapping instead makes them visible to every
    source, since that mapping is the one variable scope Textual does share globally.

    Args:
        css_text: raw TCSS source to scan for variable declarations.
        resolved: mapping of already-known variable name to resolved value, used to
            resolve `$other` references found in declaration values. Not mutated.

    Returns:
        dict[str, str]: mapping of overridden variable name to resolved value.
    """
    resolved = dict(resolved)
    overrides: dict[str, str] = {}
    depth = 0
    for line in css_text.splitlines():
        stripped = line.strip()
        if depth == 0:
            match = _VARIABLE_DECLARATION.match(stripped)
            if match is not None:
                name, value = match.groups()

                def substitute(ref_match: re.Match[str]) -> str:
                    ref_name = ref_match.group()[1:]
                    return resolved.get(ref_name, ref_match.group())

                resolved_value = _VARIABLE_REF.sub(substitute, value)
                overrides[name] = resolved_value
                resolved[name] = resolved_value
        depth += stripped.count("{") - stripped.count("}")
    return overrides


def strip_variable_declarations(css_text: str) -> str:
    """
    Remove top-level `$name: value;` declarations from a TCSS source.

    Companion to `extract_variable_overrides`: once a declaration's value is
    injected app-wide through `get_css_variables`, Textual must not see the
    declaration again — redefining a variable appends its tokens onto the
    existing value instead of replacing it, so `$x: 7;` in a file on top of an
    injected `x = 7` makes every `$x` reference resolve to `7 7`.

    Args:
        css_text: raw TCSS source.

    Returns:
        str: the source with declaration lines blanked (not removed, so error
            locations keep pointing at the right lines).
    """
    lines = css_text.splitlines()
    depth = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if depth == 0 and _VARIABLE_DECLARATION.match(stripped):
            lines[index] = ""
        depth += stripped.count("{") - stripped.count("}")
    return "\n".join(lines)
