import json
import os
from functools import cache
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from os import path
from shutil import which
from typing import Callable, cast

import fastjsonschema
import tomli
from fastjsonschema import JsonSchemaValueException
from platformdirs import user_config_dir
from rich.console import Console

from rovr.classes.config import RovrConfig

pprint = globals().get("pprint", Console().print)


EDITOR_CANDIDATES = [
    "hx",
    "nvim",
    "vim",
    "vi",
    "nano",
    "edit",
    "msedit",
]


@cache
def editor() -> str:
    for edtr in EDITOR_CANDIDATES:
        if which(edtr):
            return edtr + " --"
    if which("zed"):
        return "zed --wait --"
    if which("code"):
        return "code --wait --"
    return ""


@cache
def get_schema_validator() -> tuple[dict, Callable[[dict], None]]:
    content = resources.files("rovr.config").joinpath("schema.json").read_text("utf-8")
    _schema_dict_cache = json.loads(content)
    _schema_validator_cache = fastjsonschema.compile(_schema_dict_cache)

    return _schema_dict_cache, _schema_validator_cache


def deep_merge(old: dict, new: dict) -> dict:
    """Mini lodash merge

    Args:
        old (dict): old dictionary
        new (dict): new dictionary, to merge on top of old

    Returns:
        dict: Merged dictionary
    """
    try:
        for key, value in new.items():
            if isinstance(value, dict):
                existing = old.get(key, {})
                old[key] = deep_merge(
                    existing if isinstance(existing, dict) else {}, value
                )
            else:
                old[key] = value
    except TypeError as exc:
        pprint(
            f"Type conflict at key '{key}': cannot merge {type(value).__name__} into {type(old.get(key)).__name__}\n    {exc}\nPlease check your config for type errors. rovr will not be launching until this is resolved."
        )
        exit(1)
    except Exception as exc:
        pprint(
            f"While deep merging the default config with the userconfig, {type(exc).__name__} was raised.\n    {exc}\nSince the conflict cannot be resolved, rovr will not be launching."
        )
        exit(1)
    return old


@cache
def get_version() -> str:
    """Get version from package metadata

    Returns:
        str: Current version
    """
    try:
        return version("rovr")
    except PackageNotFoundError:
        return "master"


def toml_dump(doc_path: str, exception: tomli.TOMLDecodeError) -> None:
    """
    Dump an error message for anything related to TOML loading

    Args:
        doc_path (str): the path to the document
        exception (tomli.TOMLDecodeError): the exception that occurred
    """
    from rich.syntax import Syntax

    doc: list = exception.doc.splitlines()
    start: int = max(exception.lineno - 3, 0)
    end: int = min(len(doc), exception.lineno + 2)
    rjust: int = len(str(end + 1))
    has_past = False
    pprint(
        rjust * " "
        + f"  [bright_blue]-->[/] [white]{path.realpath(doc_path)}:{exception.lineno}:{exception.colno}[/]"
    )
    for line in range(start, end):
        if line + 1 == exception.lineno:
            startswith = "╭╴"
            has_past = True
            pprint(
                f"[bright_red]{startswith}{str(line + 1).rjust(rjust)}[/][bright_blue] │[/]",
                end=" ",
            )
        else:
            startswith = "│ " if has_past else "  "
            pprint(
                f"[bright_red]{startswith}[/][bright_blue]{str(line + 1).rjust(rjust)} │[/]",
                end=" ",
            )
        pprint(
            Syntax(
                doc[line],
                "toml",
                background_color="default",
                theme="ansi_dark",
            )
        )
    # check if it is an interesting error message
    if exception.msg.startswith("What? "):
        # What? <key> already exists?<dict>
        msg_split = exception.msg.split()
        exception.msg = f"Redefinition of [bright_cyan]{msg_split[1]}[/] is not allowed. Keep to a table, or not use one at all"
    pprint(f"[bright_red]╰─{'─' * rjust}─❯[/] {exception.msg}")
    exit(1)


def find_path_line(lines: list[str], path: list) -> int | None:
    """Find the line number for a given JSON path in TOML content

    Args:
        lines: list of lines from the TOML file
        path: the JSON path from the ValidationError

    Returns:
        int | None: the line number (0-indexed) or None if not found
    """
    if not path:
        return 0

    if path[0] == "data":
        path.pop(0)

    path_filtered = [p for p in path if not isinstance(p, int)]
    if not path_filtered:
        return 0

    current_section = []

    best_match_line: int = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for section headers [section] or [[section]] (array-of-tables)
        if stripped.startswith("["):
            # Normalize by stripping one or two surrounding brackets
            if stripped.startswith("[[") and stripped.endswith("]]"):
                section_name = stripped[2:-2].strip()
                current_section = section_name.split(".")
            else:
                section_name = stripped.strip("[]").strip()
                current_section = section_name.split(".")

            if current_section == path_filtered:
                best_match_line = i
            for depth in range(1, len(current_section) + 1):
                if current_section[:depth] == path_filtered[:depth]:
                    best_match_line = i
        elif "=" in stripped:
            key = stripped.split("=")[0].strip().strip('"').strip("'")
            full_path = current_section + [key]
            if full_path == path_filtered:
                # exact match
                best_match_line = i
                break
    return best_match_line if best_match_line != -1 else None


def schema_dump(
    doc_path: str, exception: JsonSchemaValueException, config_content: str
) -> None:
    """
    Dump an error message for schema validation errors

    Args:
        doc_path: path to the config file
        exception: the ValidationError that occurred
        config_content: the raw file content
    """
    import fnmatch

    from rich import box
    from rich.padding import Padding
    from rich.syntax import Syntax
    from rich.table import Table

    # i dont know what sort of mental illness the package has
    # to insert a data prefix to the path, but i cant blame them
    # i would also make stupid mistakes everywhere
    exception.message = exception.message.replace("data.", "")
    if exception.name is not None and exception.name.startswith("data."):
        exception.name = exception.name[5:]

    def get_message(exception: JsonSchemaValueException) -> tuple[str, bool]:
        failed = False
        match exception.rule:
            case "required":
                error_msg = f"Missing required field: {exception.message}"
            case "type":
                error_msg = f"Expected [bright_cyan]{exception.rule_definition}[/] type, but got [bright_yellow]{type(exception.value).__name__}[/] instead"
            case "enum":
                error_msg = f"'{exception.value}' is not inside allowlist of {exception.rule_definition}"
            case "minimum":
                error_msg = f"Value for [bright_cyan]{exception.name}[/] must be >= {exception.rule_definition} (cannot be {exception.value})"
            case "maximum":
                error_msg = f"Value for [bright_cyan]{exception.name}[/] must be <= {exception.rule_definition} (cannot be {exception.value})"
            case "additionalProperties":
                error_msg = exception.message
            case "uniqueItems":
                error_msg = f"[bright_cyan]{exception.name}[/] must have unique items (item '{cast(list, exception.value)[0]}' is duplicated)"
            case _:
                error_msg = exception.message
                failed = True
        return (f"schema\\[{exception.rule}]: {error_msg}", failed)

    doc: list = config_content.splitlines()

    # minor fix for additionalProperties
    if exception.rule == "additionalProperties":
        # the current message is like `<name> must not contain {<value>, <value>, ...} properties.`
        # but i want one of them only, so i have to regex it out
        # so that i can get `<value> is not allowed in <name>` or something like that
        import re

        match = re.search(r"\{([^}]+)\}", exception.message)
        if match:
            # Get the first value from the comma-separated list
            values = [v.strip() for v in match.group(1).split(",")]
            if values:
                prop = values[0]
                name_match = re.match(r"^(.+) must not contain", exception.message)
                name = name_match.group(1) if name_match else "<unknown>"
                part = f"in '{name}'" if name != "data" else "at root"
                new_message = f"{prop} is not allowed {part}"
                exception.message = new_message
                if exception.name is not None:
                    exception.name += f".{prop.strip("'")}"

    # find the line no for the error path
    # exception.path is just exception.name but as a property
    path_str = ".".join(str(p) for p in exception.path) if exception.path else "root"
    if path_str.startswith("data"):
        path_str = path_str[5:] if len(path_str) > 5 else "root"
    lineno = find_path_line(doc, exception.path)

    rjust: int = 0

    if lineno is None:
        # fallback to infoless error display
        pprint(
            f"[underline bright_red]Config Error[/] at path [bold cyan]{path_str}[/]:"
        )
        msg, failed = get_message(exception)
        if failed:
            pprint(f"[yellow]{msg}[/]")
        else:
            pprint(msg)
    else:
        start: int = max(lineno - 2, 0)
        end: int = min(len(doc), lineno + 3)
        rjust = len(str(end + 1))
        has_past = False

        pprint(
            rjust * " "
            + f"  [bright_blue]-->[/] [white]{path.realpath(doc_path)}:{lineno + 1}[/]"
        )
        for line in range(start, end):
            if line == lineno:
                startswith = "╭╴"
                has_past = True
                pprint(
                    f"[bright_red]{startswith}{str(line + 1).rjust(rjust)}[/][bright_blue] │[/]",
                    end=" ",
                )
            else:
                startswith = "│ " if has_past else "  "
                pprint(
                    f"[bright_red]{startswith}[/][bright_blue]{str(line + 1).rjust(rjust)} │[/]",
                    end=" ",
                )
            pprint(
                Syntax(
                    doc[line],
                    "toml",
                    background_color="default",
                    theme="ansi_dark",
                )
            )

        # Format the error message based on validator type
        error_msg, _ = get_message(exception)

        pprint(f"[bright_red]╰─{'─' * rjust}─❯[/] {error_msg}")
    # check path for custom message from migration.json
    migration_docs = json.loads(
        resources.files("rovr.config").joinpath("migration.json").read_text("utf-8")
    )

    for item in migration_docs:
        if any(fnmatch.fnmatch(path_str, path) for path in item["keys"]):
            message = "\n".join(item["message"])
            to_print = Table(
                box=box.ROUNDED,
                border_style="bright_blue",
                show_header=False,
                expand=True,
                show_lines=True,
            )
            to_print.add_column()
            to_print.add_row(message)
            to_print.add_row(f"[dim]> {item['extra']}[/]")
            if "regex" in item and doc_path != path.join(
                path.dirname(__file__), "../config/config.toml"
            ):
                # bird migration
                import re

                fixed_content = config_content
                for rule in item["regex"]:
                    fixed_content = re.sub(
                        re.escape(rule["find"]), rule["replace"], fixed_content
                    )
                if fixed_content != config_content:
                    with open(doc_path, "w", encoding="utf-8") as _f:
                        _f.write(fixed_content)
                    to_print.add_row(
                        "[bright_green]Auto-fix applied! Please re-run rovr.[/]"
                    )
                else:
                    to_print.add_row(
                        "[bright_yellow]I couldn't fix it for you. Please update your config manually.[/]"
                    )
            pprint(Padding(to_print, (0, rjust + 4, 0, rjust + 3)))
            break

    if exception.rule != "additionalProperties":
        exit(1)


def load_config() -> tuple[dict, RovrConfig]:
    """
    Load both the template config and the user config

    Returns:
        dict: the config
    """

    config_dir = os.environ.get("ROVR_CONFIG_FOLDER")
    if not config_dir:
        from rovr.variables.maps import RovrVars

        config_dir: str = vars(RovrVars).get("ROVRCONFIG", None) or user_config_dir(
            "rovr", "."
        ).replace("\\", "/")
    user_config_path = path.join(config_dir, "config.toml")

    # Startup path should remain read-only for existing user config.
    # Any schema header normalization is intentionally left for explicit
    # config migration/update flows, not hot startup.
    template_config: dict = {}
    try:
        template_config = tomli.loads(
            resources.files("rovr.config").joinpath("config.toml").read_text("utf-8")
        )
    except tomli.TOMLDecodeError as exc:
        toml_dump(path.join(path.dirname(__file__), "../config/config.toml"), exc)

    schema_dict, schema = get_schema_validator()

    # ensure that template config works
    try:
        schema(template_config)
    except JsonSchemaValueException as exception:
        schema_dump(
            path.join(path.dirname(__file__), "../config/config.toml"),
            exception,
            resources.files("rovr.config").joinpath("config.toml").read_text("utf-8"),
        )
        pprint(
            "        [red]I will refuse to launch as long as the template config is invalid.[/]"
        )
        exit(1)
    user_config = {}
    user_config_content = ""
    if path.exists(user_config_path):
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config_content = f.read()
            if user_config_content:
                try:
                    user_config = tomli.loads(user_config_content)
                except tomli.TOMLDecodeError as exc:
                    toml_dump(user_config_path, exc)
    # Don't really have to consider the else part, because it's created further down
    config_dict = deep_merge(template_config, user_config)
    try:
        schema(config_dict)
    except JsonSchemaValueException as exception:
        schema_dump(user_config_path, exception, user_config_content)

    # slight config fixes
    # image protocol because "AutoImage" doesn't work with Sixel
    if config_dict["interface"]["image_viewer"]["protocol"] == "Auto":
        # another no choice fix, because if Auto then
        # AutoImage is grabbed, which sucks in rendering
        # sixel for some weird unknown reason
        config_dict["interface"]["image_viewer"]["protocol"] = ""

    for key in ["file", "folder", "bulk_rename"]:
        raw_run = config_dict["settings"]["editor"][key]["run"]
        expanded_run = os.path.expandvars(raw_run)
        if expanded_run == raw_run and any(
            token in raw_run for token in ("$EDITOR", "${EDITOR}", "%EDITOR%")
        ):
            expanded_run = ""
        if not expanded_run:
            expanded_run = editor()
        config_dict["settings"]["editor"][key]["run"] = expanded_run

    # pdf fixer
    if config_dict["plugins"]["poppler"]["enabled"] and config_dict["plugins"][
        "poppler"
    ]["poppler_folder"].lower() in ("", "path"):
        pdfinfo_executable = which("pdfinfo")
        pdfinfo_path: str | None = None
        if pdfinfo_executable is None:
            config_dict["plugins"]["poppler"]["enabled"] = False
        else:
            pdfinfo_path = path.dirname(pdfinfo_executable)
        # need to ignore in this case. poppler_folder is typed as str
        # in the config schema, but pdfinfo_path can be None when
        # resolved from PATH, so we suppress the type error
        config_dict["plugins"]["poppler"]["poppler_folder"] = pdfinfo_path
    return schema_dict, cast(RovrConfig, config_dict)
