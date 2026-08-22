import json
import marshal
import os
from contextlib import suppress
from functools import cache
from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from os import path
from shutil import which
from sys import exit
from typing import Callable, cast

import fastjsonschema
import tomli
from fastjsonschema import JsonSchemaValueException
from platformdirs import user_config_dir

from rovr import pprint
from rovr.classes.config import RovrConfig
from rovr.classes.type_aliases import KeysConfig
from rovr.variables.maps import RovrVars

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


if globals().get("__compiled__"):
    traverser = resources.files("_rovr.assets")
else:
    traverser = resources.files("rovr.assets")


@cache
def get_schema_validator() -> tuple[dict, Callable[[dict], None]]:
    schema_file = traverser.joinpath("schema.json")
    mtime = path.getmtime(schema_file.as_posix())
    schema_bin = path.join(RovrVars.ROVRTEMP, "schema.marshal")
    if path.isfile(schema_bin):
        try:
            with open(schema_bin, "rb") as f:
                cached_mtime, schema_dict, code = marshal.load(f)
            if cached_mtime == mtime:
                namespace: dict = {}
                exec(code, namespace)
                return schema_dict, namespace["validate"]
        except Exception:
            pass
    schema_dict = json.loads(schema_file.read_text("utf-8"))
    try:
        code = compile(fastjsonschema.compile_to_code(schema_dict), "<schema>", "exec")
        os.makedirs(RovrVars.ROVRTEMP, exist_ok=True)
        with open(schema_bin, "wb") as f:
            marshal.dump((mtime, schema_dict, code), f)
        namespace: dict = {}
        exec(code, namespace)
        return schema_dict, namespace["validate"]
    except Exception:
        # compile directly and pass
        return schema_dict, fastjsonschema.compile(schema_dict)


def deep_merge(old: dict, new: dict) -> dict:
    """Mini lodash merge

    Args:
        old (dict): old dictionary
        new (dict): new dictionary, to merge on top of old

    Returns:
        dict: Merged dictionary with new's keys taking priority

    Raises:
        TypeError: If there is a type conflict between old and new types
    """
    try:
        result: dict = {}
        modifiers: list[tuple[str, str, list]] = []
        for key, value in new.items():
            if isinstance(value, list) and key.startswith(("prepend_", "append_")):
                prefix, base = key.split("_", 1)
                modifiers.append((prefix, base, value))
                continue
            if isinstance(value, dict):
                existing = old.get(key, {})
                result[key] = deep_merge(
                    existing if isinstance(existing, dict) else {}, value
                )
            else:
                result[key] = value
        for key, value in old.items():
            if key not in new:
                if isinstance(value, dict):
                    existing = result.get(key, {})
                    result[key] = deep_merge(existing, value)
                else:
                    result[key] = value
        for prefix, base, values in modifiers:
            target = result.get(base, old.get(base))
            if isinstance(target, list):
                result[base] = (
                    values + target if prefix == "prepend" else target + values
                )
    except TypeError as exc:
        if locals().get("key") is None and locals().get("value") is None:
            pprint(
                f"Type conflict: cannot merge {type(new).__name__} into {type(old).__name__}"
            )
        else:
            pprint(
                f"Type conflict at key '{key}': cannot merge {type(value).__name__} into {type(old.get(key)).__name__}"
            )
        pprint(
            f"    {exc}\nPlease check your config for type errors. rovr will not be launching until this is resolved."
        )
        raise
    except Exception as exc:
        pprint(
            f"While deep merging the default config with the userconfig, {type(exc).__name__} was raised.\n    {exc}\nSince the conflict cannot be resolved, rovr will not be launching."
        )
        exit(1)
    return result


def set_nested_value(
    d: dict, path_str: str, value: bool | str | int | float | list | dict
) -> None:
    """
    Sets a value in a nested dictionary using a dot-separated path string.

    Args:
        d (dict): The dictionary to modify.
        path_str (str): The dot-separated path to the key (e.g., "plugins.bat").
        value (Union[bool, str, int, float, list, dict]): The value to set.

    Raises:
        SystemExit: If the path is invalid or if there's a type mismatch when setting the value.
    """
    from rich import box
    from rich.panel import Panel

    keys = path_str.split(".")
    current = d
    passed_keys = ""
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            try:
                if (
                    isinstance(value, bool)
                    and isinstance(current[key], dict)
                    and "enabled" in current[key]
                ):
                    # Special case: For boolean values targeting plugin dicts,
                    # set the 'enabled' field rather than replacing the whole dict
                    current[key]["enabled"] = value
                elif isinstance(current[key], type(value)):
                    current[key] = value
                else:
                    pprint(
                        Panel(
                            f"[cyan bold]{path_str}[/]'s new value of type [cyan b]{type(value).__name__}[/] is not a [bold cyan]{type(current[key]).__name__}[/] type, and cannot be modified.",
                            box=box.ROUNDED,
                            title="[bright_red underline]Config Error:[/]",
                            title_align="left",
                            expand=False,
                        )
                    )
                    raise SystemExit(1)
            except KeyError:
                pprint(
                    Panel(
                        f"[cyan b]{path_str}[/] is not a valid path to an existing value and hence cannot be set.\n  [red]ValueError[/]: Key named [red b]{key}[/] was not found in [cyan b]{passed_keys[:-1]}[/]",
                        box=box.ROUNDED,
                        title="[bright_red underline]Config Error:[/]",
                        title_align="left",
                        expand=False,
                    )
                )
                raise SystemExit(1)
        else:
            if not isinstance(current.get(key), dict):
                current[key] = {}
            current = current[key]
            passed_keys += f"{key}."


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
    highlighted = (
        Syntax("", "toml", background_color="default", theme="ansi_dark")
        .highlight(exception.doc)
        .split("\n")
    )
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
        pprint(highlighted[line])
    # check if it is an interesting error message
    if exception.msg.startswith("What? "):
        # What? <key> already exists?<dict>
        msg_split = exception.msg.split()
        exception.msg = f"Redefinition of [bright_cyan]{msg_split[1]}[/] is not allowed. Keep to a table, or not use one at all"
    pprint(f"[bright_red]╰─{'─' * rjust}─❯[/] Syntax Error: {exception.msg}")
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
    temp_best_match = best_match_line = (-1, 0)
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
                temp_best_match = (i, len(current_section))
                if temp_best_match[1] > best_match_line[1]:
                    best_match_line = temp_best_match

            for depth in range(1, len(current_section) + 1):
                if current_section[:depth] == path_filtered[:depth]:
                    temp_best_match = (i, depth)
            if temp_best_match[1] > best_match_line[1]:
                best_match_line = temp_best_match
        elif "=" in stripped:
            key = stripped.split("=")[0].strip().strip('"').strip("'")
            full_path = current_section + key.split(".")
            if full_path == path_filtered:
                # exact match
                best_match_line = (i, len(full_path))
                break
            elif full_path == path_filtered[: len(full_path)]:
                # partial match, keep searching for better match
                best_match_line = (
                    (i, len(full_path))
                    if len(full_path) > best_match_line[1]
                    else best_match_line
                )
    return best_match_line[0] if best_match_line[0] != -1 else None


def schema_dump(
    doc_path: str,
    exception: JsonSchemaValueException,
    config_content: str,
    schema: dict,
    use_migration: bool = True,
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
            case "oneOf":
                error_msg = f"Value for [bright_cyan]{exception.name}[/] does not match any of the allowed schemas"
                # check specific paths because im too lazy to make it automatic
                # also it would be quite hard to ensure that either ways, so this is much easier
                print(repr(exception))
                if exception.name.startswith("settings.right_click"):
                    error_msg += "\nHint: This only supports one of the following:"
                    if exception.name.endswith("action"):
                        error_msg += f"""
    - one of {[item for item in schema["definitions"]["right_click_action"]["oneOf"][0]["enum"] if item.startswith("rovr:")]}
    - one of {[item for item in schema["definitions"]["right_click_action"]["oneOf"][0]["enum"] if item.startswith("system:")]}
    - a dictionary of {{"run" = str, "run_type" = "<one of {schema["definitions"]["right_click_action"]["oneOf"][1]["properties"]["run_type"]["enum"]}>", shell = bool}}"""
                    else:
                        error_msg += """
    - has [bright_cyan]"label"[/] and [bright_cyan]"action"[/] fields
    - has [bright_magenta]"label"[/] and [bright_magenta]"options"[/] fields for its submenu"""
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
        highlighted = (
            Syntax("", "toml", background_color="default", theme="ansi_dark")
            .highlight(config_content)
            .split("\n")
        )

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
            pprint(highlighted[line])

        # Format the error message based on validator type
        error_msg, _ = get_message(exception)

        if len(msgs := error_msg.split("\n")) != 1:
            # multi-line: display with padding
            error_msg = msgs[0]
            for part in msgs[1:]:
                error_msg += f"\n{(rjust + 5) * ' '}{part}"

        pprint(f"[bright_red]╰─{'─' * rjust}─❯[/] {error_msg}")
    if use_migration:
        # check path for custom message from migration.json
        migration_docs = json.loads(
            traverser.joinpath("migration.json").read_text("utf-8")
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
    current_version = get_version()
    if current_version == "master":
        schema_ref = "refs/heads/master"
    else:
        schema_ref = f"refs/tags/v{current_version}"

    # Startup path should remain read-only for existing user config.
    # Any schema header normalization is intentionally left for explicit
    # config migration/update flows, not hot startup.
    template_config: dict = {}
    try:
        template_config = tomli.loads(
            traverser.joinpath("config.toml").read_text("utf-8")
        )
    except tomli.TOMLDecodeError as exc:
        toml_dump(path.join(path.dirname(__file__), "../config/config.toml"), exc)

    schema_dict, schema = get_schema_validator()

    user_config = {}
    user_config_content = ""
    if path.exists(user_config_path):
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config_content = f.read()
            if user_config_content:
                try:
                    schema_url = f"https://raw.githubusercontent.com/NSPC911/rovr/{schema_ref}/src/rovr/assets/schema.json"
                    user_config = tomli.loads(user_config_content)

                    # check version
                    lines = user_config_content.splitlines()
                    expected_schema_line = f"#:schema {schema_url}"
                    if lines and lines[0] != expected_schema_line:
                        # check if it is schema in the first place
                        header = lines[0].lstrip("\ufeff").lstrip()
                        if header.startswith("#:schema"):
                            lines[0] = expected_schema_line
                        else:
                            lines.insert(0, expected_schema_line)

                        with open(user_config_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(lines))

                        display_version = (
                            f"v{current_version}"
                            if current_version != "master"
                            else "master"
                        )
                        pprint(f"[yellow]Updated config schema to {display_version}[/]")

                except tomli.TOMLDecodeError as exc:
                    toml_dump(user_config_path, exc)
    # Don't really have to consider the else part, because it's created further down
    config_dict = deep_merge(template_config, user_config)
    try:
        schema(config_dict)
    except JsonSchemaValueException as exception:
        # check template if it is wrong as well
        try:
            schema(template_config)
        except JsonSchemaValueException as template_exception:
            schema_dump(
                path.join(path.dirname(__file__), "../config/config.toml"),
                template_exception,
                traverser.joinpath("config.toml").read_text("utf-8"),
                schema_dict,
            )
        else:
            schema_dump(user_config_path, exception, user_config_content, schema_dict)
        exit(1)

    for key in ["file", "folder", "bulk_editor"]:
        raw_run = config_dict["settings"]["editor"][key]["run"]
        if isinstance(raw_run, list):
            expanded_run = [os.path.expandvars(part) for part in raw_run]
            if not expanded_run:
                expanded_run = [editor()]
            config_dict["settings"]["editor"][key]["run"] = expanded_run
        else:
            expanded_run = os.path.expandvars(raw_run)
            if expanded_run == raw_run and any(
                token in raw_run for token in ("$EDITOR", "${EDITOR}", "%EDITOR%")
            ):
                expanded_run = ""
            unresolved_editor = any(
                part in ("$EDITOR", "${EDITOR}", "%EDITOR%") for part in expanded_run
            )
            if not expanded_run or unresolved_editor or not expanded_run[0]:
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


def keys_merge(old: dict, new: dict) -> dict:
    result = old | new
    for key, value in new.items():
        if (
            isinstance(value, dict)
            and "action" not in value
            and isinstance(old.get(key), dict)
        ):
            result[key] = keys_merge(old[key], value)
    return result


def load_keys() -> KeysConfig:
    """
    Load the keybindings from the keys.toml file

    Returns:
        dict: the keybindings
    """
    config_dir = os.environ.get("ROVR_CONFIG_FOLDER")
    if not config_dir:
        from rovr.variables.maps import RovrVars

        config_dir: str = vars(RovrVars).get("ROVRCONFIG", None) or user_config_dir(
            "rovr", "."
        ).replace("\\", "/")
    user_keys_path = path.join(config_dir, "keys.toml")
    presets = {
        "base": traverser.joinpath("keys.toml"),
        "sane": traverser.joinpath("presets", "sane.toml"),
        "vim": traverser.joinpath("presets", "vim.toml"),
    }

    if not path.exists(user_keys_path):
        return {}
        # TODO: for v0.11.0: force keys.toml
        # return cast(
        #     KeysConfig, tomli.loads(presets["default"].read_text(encoding="utf-8"))
        # )

    user_keys = {}
    user_keys_content = ""
    with open(user_keys_path, "r", encoding="utf-8") as f:
        user_keys_content = f.read()
        if user_keys_content:
            try:
                user_keys = tomli.loads(user_keys_content)
            except tomli.TOMLDecodeError as exc:
                toml_dump(user_keys_path, exc)
    inherit = user_keys.pop("inherit", None)
    if inherit is not None and (not isinstance(inherit, str) or inherit not in presets):
        # find inherit in config
        lines = user_keys_content.splitlines()
        index = 0
        for i, line in enumerate(lines):
            try:
                part = tomli.loads(line)
                if "inherit" in part:
                    index = i
                    break
            except tomli.TOMLDecodeError:
                continue
        toml_dump(
            user_keys_path,
            tomli.TOMLDecodeError(
                f"Invalid inherit value '{inherit}'. Must be one of {list(presets.keys())}.",
                doc=user_keys_content,
                pos=index,
            ),
        )

    base_keys = (
        tomli.loads(presets[inherit].read_text(encoding="utf-8"))
        if isinstance(inherit, str)
        else {}
    )
    keys_dict = cast(KeysConfig, keys_merge(base_keys, user_keys))
    # check it manually
    schema = {
        "type": "object",
        "patternProperties": {
            "^.*$": {
                "type": "object",
                "patternProperties": {
                    "^.*$": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string"},
                                    "desc": {"type": "string"},
                                },
                                "required": ["action"],
                                "additionalProperties": False,
                            },
                        ]
                    },
                },
            },
        },
    }
    try:
        fastjsonschema.validate(
            schema,
            keys_dict,
        )
    except JsonSchemaValueException as exception:
        # check if 'inherits' is used, if so, alert
        with suppress(SystemExit):
            schema_dump(
                user_keys_path,
                exception,
                user_keys_content,
                schema,
                use_migration=False,
            )
        if exception.path == ["inherits"]:
            from rich import box
            from rich.padding import Padding
            from rich.table import Table

            to_print = Table(
                box=box.ROUNDED,
                border_style="bright_blue",
                show_header=False,
                expand=True,
                show_lines=True,
            )
            to_print.add_column()
            to_print.add_row(
                "[bright_red]Config Error:[/] 'inherits' is not a valid key in keys.toml. Please use 'inherit' instead."
            )
            pprint(Padding(to_print, (0, 4, 0, 3), expand=False))
        exit(1)

    return {
        context: {
            key: {"action": binding} if isinstance(binding, str) else binding
            for key, binding in context_keys.items()
        }
        for context, context_keys in keys_dict.items()
    }
