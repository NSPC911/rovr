import os
from collections import deque
from importlib.metadata import PackageNotFoundError, version
from os import path

import jsonschema
import toml
import ujson
from jsonschema import ValidationError
from lzstring import LZString
from rich.console import Console

from rovr.functions.utils import deep_merge
from rovr.variables.maps import (
    VAR_TO_DIR,
)

lzstring = LZString()
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


def toml_dump(doc_path: str, exception: toml.TomlDecodeError) -> None:
    """
    Dump an error message for anything related to TOML loading

    Args:
        doc_path (str): the path to the document
        exception (toml.TomlDecodeError): the exception that occurred
    """
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
        if "[" in doc[line]:
            doc[line] = doc[line].replace("[", "\\[")
        if line + 1 == exception.lineno:
            startswith = "╭╴"
            has_past = True
            pprint(
                f"[bright_red]{startswith}{str(line + 1).rjust(rjust)}[/][bright_blue] │[/] {doc[line]}"
            )
        else:
            startswith = "│ " if has_past else "  "
            pprint(
                f"[bright_red]{startswith}[/][bright_blue]{str(line + 1).rjust(rjust)} │[/] {doc[line]}"
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
    doc: list = config_content.splitlines()

    # find the line no for the error path
    path_str = ".".join(str(p) for p in exception.path) if exception.path else "root"
    lineno = find_path_line(doc, exception.path)

    if lineno is None:
        # fallback to infoless error display
        pprint(
            f"[underline bright_red]Config Error[/] at path [bold cyan]{path_str}[/]:"
        )
        match exception.validator:
            case "required":
                pprint(f"{exception.message}, but is not provided.")
            case "type":
                type_error_message = (
                    f"Invalid type: expected [yellow]{exception.validator_value}[/yellow], "
                    f"but got [yellow]{type(exception.instance).__name__}[/yellow]."
                )
                pprint(type_error_message)
            case "enum":
                enum_error_message = (
                    f"Invalid value [yellow]'{exception.instance}'[/yellow]. "
                    f"\nAllowed values are: {exception.validator_value}"
                )
                pprint(enum_error_message)
            case _:
                pprint(f"[yellow]{exception.message}[/yellow]")
    else:
        start: int = max(lineno - 2, 0)
        end: int = min(len(doc), lineno + 3)
        rjust: int = len(str(end + 1))
        has_past = False

        pprint(
            rjust * " "
            + f"  [bright_blue]-->[/] [white]{path.realpath(doc_path)}:{lineno + 1}[/]"
        )
        for line in range(start, end):
            if "[" in doc[line]:
                doc[line] = doc[line].replace("[", "\\[")
            if line == lineno:
                startswith = "╭╴"
                has_past = True
                pprint(
                    f"[bright_red]{startswith}{str(line + 1).rjust(rjust)}[/][bright_blue] │[/] {doc[line]}"
                )
            else:
                startswith = "│ " if has_past else "  "
                pprint(
                    f"[bright_red]{startswith}[/][bright_blue]{str(line + 1).rjust(rjust)} │[/] {doc[line]}"
                )

        # Format the error message based on validator type
        match exception.validator:
            case "required":
                error_msg = f"Missing required field: {exception.message}"
            case "type":
                error_msg = f"Expected [bright_cyan]{exception.validator_value}[/] type, but got [bright_yellow]{type(exception.instance).__name__}[/] instead"
            case "enum":
                error_msg = f"Provided value '{exception.instance}' is not inside allowlist of {exception.validator_value}"
            case "minimum":
                error_msg = f"Value for [bright_cyan]{'.'.join(map(str, exception.relative_path))}[/] must be >= {exception.validator_value} (cannot be {exception.instance})"
            case "maximum":
                error_msg = f"Value for [bright_cyan]{'.'.join(map(str, exception.relative_path))}[/] must be <= {exception.validator_value} (cannot be {exception.instance})"
            case _:
                error_msg = exception.message

        pprint(f"[bright_red]╰─{'─' * rjust}─❯[/] {error_msg}")
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

    with open(path.join(path.dirname(__file__), "../config/config.toml"), "r", encoding="utf-8") as f:
        # check header
        try:
            content = f.read()
            template_config = toml.loads(content)
        except toml.TomlDecodeError as exc:
            toml_dump(path.join(path.dirname(__file__), "../config/config.toml"), exc)

    user_config = {}
    user_config_content = ""
    if path.exists(user_config_path):
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config_content = f.read()
            if user_config_content:
                try:
                    user_config = toml.loads(user_config_content)
                except toml.TomlDecodeError as exc:
                    toml_dump(user_config_path, exc)
    # Don't really have to consider the else part, because it's created further down
    config = deep_merge(template_config, user_config)
    # check with schema
    with open(path.join(path.dirname(__file__), "../config/schema.json"), "r", encoding="utf-8") as f:
        content = f.read()
        schema = ujson.loads(content)

    try:
        jsonschema.validate(config, schema)
    except ValidationError as exception:
        schema_dump(user_config_path, exception, user_config_content)

    # slight config fixes
    # image protocol because "AutoImage" doesn't work with Sixel
    if config["settings"]["image_protocol"] == "Auto":
        config["settings"]["image_protocol"] = ""
    return schema, config


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
