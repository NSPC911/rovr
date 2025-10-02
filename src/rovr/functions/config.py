import os
from os import path
from typing import Optional

import jsonschema
import toml
import ujson
from lzstring import LZString
from rich.console import Console

from rovr.functions.utils import deep_merge
from rovr.variables.maps import (
    VAR_TO_DIR,
)

lzstring = LZString()
pprint = Console().print


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load and merge template config with user config (default or custom path).
    
    This function implements the core config loading strategy:
    1. Load template config (contains all default values)
    2. Load user config (either default location or custom path via -c flag)
    3. Deep merge user config over template (user settings override defaults)
    4. Validate merged config against JSON schema
    
    Args:
        config_path: Optional path to custom config file. If None, uses default user config.
        
    Returns:
        dict: Merged and validated configuration
    """
    
    # Ensure config directory exists for default user config
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    
    # Create default user config if it doesn't exist (minimal config to get started)
    default_user_config_path = path.join(VAR_TO_DIR["CONFIG"], "config.toml")
    if not path.exists(default_user_config_path):
        with open(default_user_config_path, "w") as file:
            file.write(
                '#:schema  https://raw.githubusercontent.com/NSPC911/rovr/refs/heads/master/src/rovr/config/schema.json\n[theme]\ndefault = "nord"'
            )

    # Load template config from package directory (contains all default values)
    with open(path.join(path.dirname(__file__), "../config/config.toml"), "r") as f:
        try:
            template_config = toml.loads(f.read())
        except toml.decoder.TomlDecodeError as e:
            pprint(f"[bright_red]Template Config TOML Syntax Error:\n    {e}")
            exit(1)

    # Determine which user config to load: custom path (if provided via -c) or default
    user_config_path = config_path if config_path else default_user_config_path
    user_config = {}
    
    if path.isdir(user_config_path):
        pprint(f"[bright_red]Provided config path is a directory: {user_config_path}[/bright_red]")
        exit(1)
    if path.isfile(user_config_path):
        # Load and parse user config file with proper error handling
        try:
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config_content = f.read()
        except OSError as e:
            pprint(f"[bright_red]Unable to read config file {user_config_path}: {e}[/bright_red]")
            exit(1)
        if user_config_content:
            try:
                user_config = toml.loads(user_config_content)
            except toml.decoder.TomlDecodeError as e:
                pprint(f"[bright_red]User Config TOML Syntax Error in {user_config_path}:\n    {e}")
                exit(1)
    elif config_path:
        # Warn user if they specified a config file that doesn't exist
        pprint(f"[yellow]Warning: Custom config file not found: {config_path}[/yellow]")
        pprint("[yellow]Falling back to your default config.[/yellow]")
        # Load the default user config instead of empty dict
        user_config_path = default_user_config_path
        if path.isdir(user_config_path):
            pprint(f"[bright_red]Default config path is a directory: {user_config_path}[/bright_red]")
            exit(1)
        if path.isfile(user_config_path):
            try:
                with open(user_config_path, "r", encoding="utf-8") as f:
                    user_config_content = f.read()
            except OSError as e:
                pprint(f"[bright_red]Unable to read default config file {user_config_path}: {e}[/bright_red]")
                exit(1)
            if user_config_content:
                try:
                    user_config = toml.loads(user_config_content)
                except toml.decoder.TomlDecodeError as e:
                    pprint(f"[bright_red]User Config TOML Syntax Error in {user_config_path}:\n    {e}")
                    exit(1)

    # Merge template config with user config (user settings override template defaults)
    # Don't really have to consider the else part, because it's created further down
    config = deep_merge(template_config, user_config)
    
    # check with schema
    with open(path.join(path.dirname(__file__), "../config/schema.json"), "r") as f:
        schema = ujson.load(f)

    # fix schema with 'required' keys
    def add_required_recursively(node: dict) -> None:
        if isinstance(node, dict):
            if (
                node.get("type") == "object" and "properties" in node
            ) and "required" not in node:
                node["required"] = list(node["properties"].keys())
            for key in node:
                add_required_recursively(node[key])
        elif isinstance(node, list):
            for item in node:
                add_required_recursively(item)

    add_required_recursively(schema)

    try:
        jsonschema.validate(config, schema)
    except jsonschema.exceptions.ValidationError as exception:
        # pprint(exception.__dict__)
        path_str = "root"
        if exception.path:
            path_str = ".".join(str(p) for p in exception.path)
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
        exit(1)

    # slight config fixes
    # image protocol because "AutoImage" doesn't work with Sixel
    if config["settings"]["image_protocol"] == "Auto":
        config["settings"]["image_protocol"] = ""
    return config


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