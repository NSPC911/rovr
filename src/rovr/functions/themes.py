import re
from contextlib import suppress
from importlib import resources
from pathlib import Path

from textual.app import App
from textual.color import Color
from textual.theme import Theme

from rovr.variables.maps import RovrVars

_VARIABLE_DECLARATION = re.compile(r"^\$([\w-]+)\s*:\s*(.+?)\s*;\s*$")
_VARIABLE_REF = re.compile(r"\$[\w-]+")
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(css_text: str) -> str:
    """
    Blank the contents of `/* ... */` comments, keeping every newline.

    Args:
        css_text: raw TCSS source.

    Returns:
        str: `css_text` with comment interiors replaced by blank lines.
    """
    return _COMMENT.sub(lambda match: "\n" * match.group().count("\n"), css_text)


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
# rovr-specific extras, declared in theme files but consumed outside CSS:
# `$bar-gradient-<kind>: <color> <color> ...;` colors the progress bars
BAR_GRADIENT_FIELDS = {
    "bar-gradient-default": "default",
    "bar-gradient-error": "error",
}


def extract_variable_declarations(css_text: str) -> dict[str, str]:
    """
    Extract top-level `$name: value;` declarations from a TCSS source, unresolved.

    Values are kept as written (`$other` references untouched) so that all files'
    declarations can be merged before any reference is resolved. Resolving at
    extraction time would freeze e.g. `$border-focused: $primary-lighten-3;` to
    whatever `$primary-lighten-3` was in an earlier file.

    Args:
        css_text: raw TCSS source to scan for variable declarations.

    Returns:
        dict[str, str]: mapping of variable name to raw declared value.
    """
    declared: dict[str, str] = {}
    depth = 0
    for line in _strip_comments(css_text).splitlines():
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


def parse_theme_file(theme_file: Path) -> Theme:
    """
    Parse a theme TCSS file into a Theme named after the file.

    Args:
        theme_file: Path to the theme file.

    Returns:
        The Theme to register.

    Raises:
        ValueError: If the theme does not define $primary.
    """
    css_text = theme_file.read_text(encoding="utf-8")
    declared = extract_variable_declarations(css_text)
    fields = pop_theme_field_overrides(declared)
    if "primary" not in fields:
        raise ValueError("a theme must define $primary")
    bar_gradient: dict[str, list[str]] = {}
    for name, kind in BAR_GRADIENT_FIELDS.items():
        if name not in declared:
            continue
        colors = declared.pop(name).split()
        for color in colors:
            Color.parse(color)
        bar_gradient[kind] = colors
    theme = Theme(
        name=theme_file.stem,
        variables=declared,
        **fields,  # ty: ignore[invalid-argument-type]
    )
    if bar_gradient:
        # consumed by ProcessContainer via getattr; not a Theme field
        theme.bar_gradient = bar_gradient  # ty: ignore[unresolved-attribute]
    css_rules = strip_variable_declarations(css_text)
    if _COMMENT.sub("", css_rules).strip():
        # css rules applied only while the theme is active; injected as a
        # stylesheet source by Application._load_theme_css via getattr
        theme.css = css_rules  # ty: ignore[unresolved-attribute]
    return theme


def theme_dirs() -> list[Path]:
    """
    The directories theme files are loaded from, in ascending priority.

    Bundled themes are registered straight from the package (never copied),
    so improvements to them reach users on upgrade; a file with the same
    name in the user theme folder overrides the bundled one.

    Returns:
        list[Path]: bundled themes directory first, user theme folder last.
    """
    dirs: list[Path] = []
    bundled_dir = Path(str(bundled_themes_path))
    if bundled_dir.is_dir():
        dirs.append(bundled_dir)
    dirs.append(Path(RovrVars.ROVRTHEMES))
    return dirs


def register_all_themes(app: App) -> list[str]:
    """
    Register every bundled and user theme file.

    Args:
        app: The application to register themes on.

    Returns:
        list[str]: human-readable errors for files that failed to parse.
    """
    Path(RovrVars.ROVRTHEMES).mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for theme_dir in theme_dirs():
        for theme_file in sorted(theme_dir.glob("*.tcss")):
            try:
                theme = parse_theme_file(theme_file)
            except Exception as exc:
                errors.append(f"{theme_file.name}: {exc}")
                continue
            app.register_theme(theme)
    return errors


def theme_file_mtimes() -> dict[str, float]:
    """
    Snapshot the modification times of every theme file.

    Returns:
        dict[str, float]: mapping of theme file path to its mtime.
    """
    mtimes: dict[str, float] = {}
    for theme_dir in theme_dirs():
        for theme_file in theme_dir.glob("*.tcss"):
            with suppress(OSError):
                mtimes[str(theme_file)] = theme_file.stat().st_mtime
    return mtimes


def strip_variable_declarations(css_text: str) -> str:
    """
    Remove top-level `$name: value;` declarations from a TCSS source.

    Once a declaration's value is
    injected app-wide through `get_css_variables`, Textual must not see the
    declaration again. Redefining a variable appends its tokens onto the
    existing value instead of replacing it, so `$x: 7;` in a file on top of an
    injected `x = 7` makes every `$x` reference resolve to `7 7`.

    Args:
        css_text: raw TCSS source.

    Returns:
        str: the source with declaration lines blanked (not removed, so error
            locations keep pointing at the right lines).
    """
    lines = css_text.splitlines()
    # scanned separately from `lines` so a commented-out `$name: value;` is
    # neither mistaken for a real declaration nor left to skew brace depth,
    # while the original comment text is still preserved in the output
    scan_lines = _strip_comments(css_text).splitlines()
    depth = 0
    for index, scan_line in enumerate(scan_lines):
        stripped = scan_line.strip()
        if depth == 0 and _VARIABLE_DECLARATION.match(stripped):
            lines[index] = ""
        depth += stripped.count("{") - stripped.count("}")
    return "\n".join(lines)
