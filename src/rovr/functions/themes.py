import re
from importlib import resources
from pathlib import Path
from shutil import copy

from textual.app import App
from textual.color import Color
from textual.theme import Theme

from rovr.classes.theme import RovrThemeClass
from rovr.variables.constants import config
from rovr.variables.maps import RovrVars

_VARIABLE_DECLARATION = re.compile(r"^\$([\w-]+)\s*:\s*(.+?)\s*;\s*$")
_VARIABLE_REF = re.compile(r"\$[\w-]+")
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

bundled_themes_path = (
    resources.files("_rovr.config")
    if globals().get("__compiled__")
    else resources.files("rovr.config")
) / "themes"

# Theme dataclass fields, keyed by the $variable name that maps onto them.
THEME_COLOR_FIELDS = frozenset({
    "primary",
    "secondary",
    "warning",
    "error",
    "success",
    "accent",
    "foreground",
    "background",
    "surface",
    "panel",
    "boost",
})
THEME_BOOL_FIELDS = frozenset({"dark", "ansi"})
THEME_FLOAT_FIELDS = frozenset({"luminosity-spread", "text-alpha"})


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


def extract_variable_declarations(css_text: str) -> dict[str, str]:
    """
    Extract top-level `$name: value;` declarations from a TCSS source, unresolved.

    Textual only shares `$variables` within the single source they're declared in,
    so a user's style.tcss can't override a variable used by the bundled style.tcss
    just by being loaded as a second CSS source. Folding the user's declarations into
    the app-wide `get_css_variables()` mapping instead makes them visible to every
    source, since that mapping is the one variable scope Textual does share globally.

    Values are kept as written (`$other` references untouched) so that all files'
    declarations can be merged before any reference is resolved — resolving at
    extraction time would freeze e.g. `$border-focused: $primary-lighten-3;` to
    whatever `$primary-lighten-3` was in an earlier file.

    Args:
        css_text: raw TCSS source to scan for variable declarations.

    Returns:
        dict[str, str]: mapping of variable name to raw declared value.
    """
    declared: dict[str, str] = {}
    depth = 0
    for line in css_text.splitlines():
        stripped = line.strip()
        if depth == 0:
            match = _VARIABLE_DECLARATION.match(stripped)
            if match is not None:
                name, value = match.groups()
                declared[name] = value
        depth += stripped.count("{") - stripped.count("}")
    return declared


def resolve_variable_references(
    declared: dict[str, str], base: dict[str, str]
) -> dict[str, str]:
    """
    Resolve `$other` references in declared values against base + declared.

    Substitution repeats until values stop changing, so chains like
    `$a: $b; $b: $c;` resolve regardless of declaration order. Reference cycles
    can never settle; the pass cap leaves their `$refs` in place rather than
    looping forever.

    Args:
        declared: mapping of variable name to raw declared value. Not mutated.
        base: already-resolved variables that references may point at. Not mutated.

    Returns:
        dict[str, str]: `declared` with every resolvable reference substituted.
    """
    resolved = dict(base)
    resolved.update(declared)

    def substitute(ref_match: re.Match[str]) -> str:
        return resolved.get(ref_match.group()[1:], ref_match.group())

    for _ in range(len(declared) + 1):
        changed = False
        for name in declared:
            new_value = _VARIABLE_REF.sub(substitute, resolved[name])
            if new_value != resolved[name]:
                resolved[name] = new_value
                changed = True
        if not changed:
            break
    return {name: resolved[name] for name in declared}


def pop_theme_field_overrides(
    declared: dict[str, str],
) -> dict[str, str | bool | float]:
    """
    Pop declarations that map onto `textual.theme.Theme` dataclass fields.

    Routing these through the Theme (and so through `ColorSystem.generate()`)
    instead of injecting them as plain variables is what makes an overridden
    `$primary` propagate to `$primary-lighten-3`, `$text-primary`, and every
    other generated variant.

    Args:
        declared: mapping of variable name to raw declared value. Matched
            names are removed.

    Returns:
        dict: keyword arguments for `dataclasses.replace` on a Theme.
    """
    fields: dict[str, str | bool | float] = {}
    for name in list(declared):
        value = declared[name]
        if name in THEME_COLOR_FIELDS:
            # a reference can't be resolved this early; leave it as a
            # plain (non-propagating) variable override
            if "$" in value:
                continue
            fields[name] = value
        elif name in THEME_BOOL_FIELDS:
            fields[name] = value.lower() in ("true", "yes", "1")
        elif name in THEME_FLOAT_FIELDS:
            try:
                fields[name.replace("-", "_")] = float(value)
            except ValueError:
                continue
        else:
            continue
        del declared[name]
    return fields


def parse_theme_file(theme_file: Path) -> tuple[Theme, list[str]]:
    """
    Parse a theme TCSS file into a Theme named after the file.

    Args:
        theme_file: Path to the theme file.

    Returns:
        A tuple of (Theme to register, human-readable warnings).

    Raises:
        ValueError: If the theme does not define $primary.
    """
    css_text = theme_file.read_text(encoding="utf-8")
    declared = extract_variable_declarations(css_text)
    fields = pop_theme_field_overrides(declared)
    if "primary" not in fields:
        raise ValueError("a theme must define $primary")
    warnings = []
    if _COMMENT.sub("", strip_variable_declarations(css_text)).strip():
        warnings.append(
            f"{theme_file.name}: css rules in theme files aren't supported yet"
        )
    return Theme(
        name=theme_file.stem,
        variables=declared,
        **fields,  # ty: ignore[invalid-argument-type]
    ), warnings


def register_all_themes(app: App) -> list[str]:
    """
    Copy bundled themes into the user theme folder, then register every theme.

    Args:
        app: The application to register themes on.

    Returns:
        list[str]: human-readable errors for files that failed to parse.
    """
    custom_dir = Path(RovrVars.ROVRTHEMES)
    custom_dir.mkdir(parents=True, exist_ok=True)
    if bundled_themes_path.is_dir():
        for bundled in bundled_themes_path.iterdir():
            target = custom_dir / bundled.name
            if not target.exists():
                copy(str(bundled), target)
    errors: list[str] = []
    for theme_file in sorted(custom_dir.glob("*.tcss")):
        try:
            theme, warnings = parse_theme_file(theme_file)
        except Exception as exc:
            errors.append(f"{theme_file.name}: {exc}")
            continue
        errors.extend(warnings)
        app.register_theme(theme)
    return errors


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
