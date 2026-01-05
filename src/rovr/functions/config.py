import os
from collections import deque
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from os import environ, path
from platform import system
from shutil import which

import jsonschema
import tomli
import ujson
from jsonschema import ValidationError
from rich import box
from rich.console import Console

from rovr.functions.utils import deep_merge, set_nested_value
from rovr.variables.maps import (
    VAR_TO_DIR,
)

pprint = Console().print

DEFAULT_CONFIG = '#:schema {schema_url}\n[theme]\ndefault = "nord"'


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


def find_path_line(lines: list[str], path: deque) -> int | None:
    """Find the line number for a given JSON path in TOML content

    Args:
        lines: list of lines from the TOML file
        path: the JSON path from the ValidationError

    Returns:
        int | None: the line number (0-indexed) or None if not found
    """
    if not path:
        return 0

    current_section = []

    # Convert path to list and filter out indices for comparison
    path_list = list(path)
    path_without_indices = [p for p in path_list if not isinstance(p, int)]

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

            if current_section in (path_without_indices, path_list):
                return i
        elif "=" in stripped:
            key = stripped.split("=")[0].strip().strip('"').strip("'")
            full_path = current_section + [key]
            if full_path in (path_without_indices, path_list):
                return i

    return None


def schema_dump(doc_path: str, exception: ValidationError, config_content: str) -> None:
    """
    Dump an error message for schema validation errors

    Args:
        doc_path: path to the config file
        exception: the ValidationError that occurred
        config_content: the raw file content
    """
    import fnmatch

    from rich.padding import Padding
    from rich.syntax import Syntax
    from rich.table import Table

    def get_message(exception: ValidationError) -> tuple[str, bool]:
        failed = False
        match exception.validator:
            case "required":
                error_msg = f"Missing required field: {exception.message}"
            case "type":
                error_msg = f"Expected [bright_cyan]{exception.validator_value}[/] type, but got [bright_yellow]{type(exception.instance).__name__}[/] instead"
            case "enum":
                error_msg = f"Provided value '{exception.instance}' is not inside allowlist of {exception.validator_value}"
            case "minimum":
                error_msg = f"Value for [bright_cyan]{'.'.join(str(p) for p in exception.relative_path)}[/] must be >= {exception.validator_value} (cannot be {exception.instance})"
            case "maximum":
                error_msg = f"Value for [bright_cyan]{'.'.join(str(p) for p in exception.relative_path)}[/] must be <= {exception.validator_value} (cannot be {exception.instance})"
            case _:
                error_msg = exception.message
                failed = True
        return (f"schema\\[{exception.validator}]: {error_msg}", failed)

    doc: list = config_content.splitlines()

    if exception.message.startswith("Additional properties are not allowed"):
        # `Additional properties are not allowed ('<key>' was unexpected)`
        # grabs only the key
        cause = exception.message.split("'")
        if len(cause) == 3:
            exception.path.append(cause[1])
        else:
            pass
    # find the line no for the error path
    path_str = ".".join(str(p) for p in exception.path) if exception.path else "root"
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
    with open(
        resources.files("rovr.config") / "migration.json", "r", encoding="utf-8"
    ) as f:
        migration_docs = ujson.load(f)

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
            pprint(Padding(to_print, (0, rjust + 4, 0, rjust + 3)))
            break
    exit(1)


def load_config() -> tuple[dict, dict]:
    """
    Load both the template config and the user config

    Returns:
        dict: the config
    """

    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])

    current_version = get_version()
    if current_version == "master":
        schema_ref = "refs/heads/master"
    else:
        schema_ref = f"refs/tags/v{current_version}"
    schema_url = f"https://raw.githubusercontent.com/NSPC911/rovr/{schema_ref}/src/rovr/config/schema.json"
    user_config_path = path.join(VAR_TO_DIR["CONFIG"], "config.toml")

    # Create config file if it doesn't exist
    if not path.exists(user_config_path):
        with open(user_config_path, "w", encoding="utf-8") as file:
            file.write(DEFAULT_CONFIG.format(schema_url=schema_url))
    else:
        # Update schema version if needed
        with open(user_config_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        expected_schema_line = f"#:schema {schema_url}\n"
        if lines and lines[0] != expected_schema_line:
            # check if it is schema in the first place
            header = lines[0].lstrip("\ufeff").lstrip()
            if header.startswith("#:schema"):
                lines[0] = expected_schema_line
            else:
                lines.insert(0, expected_schema_line)

            with open(user_config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            display_version = (
                f"v{current_version}" if current_version != "master" else "master"
            )
            pprint(f"[yellow]Updated config schema to {display_version}[/]")
        elif not lines:
            with open(user_config_path, "w", encoding="utf-8") as file:
                file.write(DEFAULT_CONFIG.format(schema_url=schema_url))
    try:
        template_config = tomli.loads(
            resources.files("rovr.config").joinpath("config.toml").read_text("utf-8")
        )
    except tomli.TOMLDecodeError as exc:
        toml_dump(path.join(path.dirname(__file__), "../config/config.toml"), exc)

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
    config = deep_merge(template_config, user_config)
    # check with schema
    content = resources.files("rovr.config").joinpath("schema.json").read_text("utf-8")
    schema = ujson.loads(content)

    try:
        jsonschema.validate(config, schema)
    except ValidationError as exception:
        if exception.validator == "additionalProperties":
            # message: "Additional properties are not allowed ('flag' was unexpected)"
            # can be was or were, depends on flags count
            flags = exception.message.split("(")[1].split(" was")[0].split(" were")[0].replace("'", "")
            pprint(f"[yellow]Warning:[/] Ignoring additional config key [bright_cyan]{flags}[/] (not in schema)")
        else:
            schema_dump(user_config_path, exception, user_config_content)

    # slight config fixes
    # image protocol because "AutoImage" doesn't work with Sixel
    if config["interface"]["image_protocol"] == "Auto":
        config["interface"]["image_protocol"] = ""
    # editor empty use $EDITOR
    if config["plugins"]["editor"]["file_executable"] == "":
        config["plugins"]["editor"]["file_executable"] = environ.get(
            "EDITOR", "nano" if system() != "Windows" else "notepad"
        )
    if config["plugins"]["editor"]["folder_executable"] == "":
        config["plugins"]["editor"]["folder_executable"] = environ.get(
            "EDITOR", "vim" if system() != "Windows" else "code"
        )
    # pdf fixer
    if (
        config["plugins"]["poppler"]["enabled"]
        and config["plugins"]["poppler"]["poppler_folder"] == ""
    ):
        pdfinfo_executable = which("pdfinfo")
        pdfinfo_path: str | None = None
        if pdfinfo_executable is None:
            config["plugins"]["poppler"]["enabled"] = False
        else:
            pdfinfo_path = path.dirname(pdfinfo_executable)
        config["plugins"]["poppler"]["poppler_folder"] = pdfinfo_path
    return schema, config


def apply_mode(config: dict, mode_name: str) -> None:
    """
    Apply mode-specific config overrides to the config dictionary.

    Args:
        config (dict): The config dictionary to modify (modified in-place)
        mode_name (str): The name of the mode to apply
    """
    if "mode" not in config:
        from rich.syntax import Syntax

        pprint("[bright_red]Error:[/] No modes defined in config")
        pprint("[yellow]Hint:[/] Define modes in config.toml like:")
        print()
        pprint(
            Syntax(
                "[mode.gui]",
                lexer="toml",
                background_color="default",
                theme="ansi_dark",
            )
        )
        pprint(
            Syntax(
                '"plugins.editor.file_executable" = "vscode"',
                lexer="toml",
                background_color="default",
                theme="ansi_dark",
            )
        )
        print()
        exit(1)

    if mode_name not in config["mode"]:
        available_modes = ", ".join(f"'{m}'" for m in config["mode"])
        pprint(f"[bright_red]Error:[/] Mode '{mode_name}' not found in config")
        pprint(f"[yellow]Available modes:[/] {available_modes}")
        exit(1)

    mode_config = config["mode"][mode_name]

    for path_str, value in mode_config.items():
        set_nested_value(config, path_str, value)

    if "mode" in config:
        del config["mode"]


def config_setup() -> None:
    # check config folder
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    # Textual doesn't seem to have a way to check whether the
    # CSS file exists while it is in operation, but textual
    # only craps itself when it can't find it as the app starts
    # so no issues
    if not path.exists(path.join(VAR_TO_DIR["CONFIG"], "style.tcss")):
        with open(path.join(VAR_TO_DIR["CONFIG"], "style.tcss"), "a") as _:
            pass
