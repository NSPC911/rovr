from importlib import resources
from pathlib import Path
from shutil import copy

from textual.app import App
from textual.css.tokenize import tokenize
from textual.theme import Theme

from rovr.variables.maps import RovrVars

bundled_themes_path = (
    resources.files("_rovr.config")
    if globals().get("__compiled__")
    else resources.files("rovr.config")
) / "themes"

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


def split_theme_source(
    source: str, read_from: tuple[str, str]
) -> tuple[dict[str, str], str]:
    """Split theme TCSS into top-level variable definitions and rule CSS.

    Variable definitions must never reach the stylesheet parser: defining a
    theme variable (like $panel) inside parsed CSS appends tokens to the
    shared definition instead of replacing it, corrupting every stylesheet
    parsed afterwards.

    Args:
        source: The theme TCSS source.
        read_from: The CSS location, for error messages.

    Returns:
        A tuple of (variable name to value mapping, remaining rule CSS).
    """
    variables: dict[str, str] = {}
    rule_parts: list[str] = []
    tokens = iter(tokenize(source, read_from))
    for token in tokens:
        if token.name == "variable_name":
            name = token.value[1:-1]
            value_parts: list[str] = []
            for value_token in tokens:
                if value_token.name == "variable_value_end":
                    break
                value_parts.append(value_token.value)
            variables[name] = "".join(value_parts).strip()
        else:
            rule_parts.append(token.value)
    return variables, "".join(rule_parts).strip()


def parse_theme_file(theme_file: Path) -> tuple[Theme, str]:
    """Parse a theme TCSS file into a Theme and its extra rule CSS.

    Args:
        theme_file: Path to the theme file.

    Returns:
        A tuple of (Theme to register, rule CSS to apply while active).

    Raises:
        ValueError: If the theme does not define $primary.
    """
    variables, rules = split_theme_source(
        theme_file.read_text(encoding="utf-8"), (str(theme_file), "")
    )
    fields: dict[str, str | bool | float] = {}
    extra_variables: dict[str, str] = {}
    for name, value in variables.items():
        if name in THEME_COLOR_FIELDS:
            fields[name] = value
        elif name in THEME_BOOL_FIELDS:
            fields[name] = value.lower() in ("true", "yes", "1")
        elif name in THEME_FLOAT_FIELDS:
            fields[name.replace("-", "_")] = float(value)
        else:
            extra_variables[name] = value
    if "primary" not in fields:
        raise ValueError("a theme must define $primary")
    return Theme(
        name=theme_file.stem,
        variables=extra_variables,
        **fields,  # ty: ignore[invalid-argument-type]
    ), rules


def register_all_themes(app: App) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Copy bundled themes to the user theme folder, then register every theme.

    Args:
        app: The application to register themes on.

    Returns:
        A tuple of (theme name to (file path, rule CSS) mapping for themes
        with extra rules, human-readable errors for files that failed).
    """
    custom_dir = Path(RovrVars.ROVRTHEMES)
    custom_dir.mkdir(parents=True, exist_ok=True)
    if bundled_themes_path.is_dir():
        for bundled in bundled_themes_path.iterdir():
            target = custom_dir / bundled.name
            if not target.exists():
                copy(str(bundled), target)
    theme_rules: dict[str, tuple[str, str]] = {}
    errors: list[str] = []
    for theme_file in sorted(custom_dir.glob("*.tcss")):
        try:
            theme, rules = parse_theme_file(theme_file)
        except Exception as exc:
            errors.append(f"{theme_file.name}: {exc}")
            continue
        app.register_theme(theme)
        if rules:
            theme_rules[theme.name] = (str(theme_file), rules)
    return theme_rules, errors
