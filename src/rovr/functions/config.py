import os
from os import path

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


def load_config() -> dict:
    """
    Load both the template config and the user config

    Returns:
        dict: the config
    """

    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    if not path.exists(path.join(VAR_TO_DIR["CONFIG"], "config.toml")):
        with open(path.join(VAR_TO_DIR["CONFIG"], "config.toml"), "w") as file:
            file.write(
                '#:schema  https://raw.githubusercontent.com/NSPC911/rovr/refs/heads/master/src/rovr/config/schema.json\n[theme]\ndefault = "nord"'
            )

    with open(path.join(path.dirname(__file__), "../config/config.toml"), "r") as f:
        try:
            template_config = toml.loads(f.read())
        except toml.decoder.TomlDecodeError as e:
            pprint(f"[bright_red]TOML Syntax Error:\n    {e}")
            exit(1)

    user_config_path = path.join(VAR_TO_DIR["CONFIG"], "config.toml")
    user_config = {}
    if path.exists(user_config_path):
        with open(user_config_path, "r") as f:
            user_config_content = f.read()
            if user_config_content:
                user_config = toml.loads(user_config_content)
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
    
    # Load saved state and merge it into config
    saved_state = load_state()
    if saved_state:
        config["state"] = saved_state
    
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


def save_state(state_data: dict) -> None:
    """
    Save application state to a separate state file.
    
    Args:
        state_data (dict): Dictionary containing state data to save
    """
    state_file_path = path.join(VAR_TO_DIR["CONFIG"], "state.json")
    
    # Load existing state if it exists
    existing_state = {}
    if path.exists(state_file_path):
        try:
            with open(state_file_path, "r") as f:
                existing_state = ujson.load(f)
        except (ujson.JSONDecodeError, IOError):
            existing_state = {}
    
    # Merge new state with existing state
    existing_state.update(state_data)
    
    # Save the updated state
    try:
        with open(state_file_path, "w") as f:
            ujson.dump(existing_state, f, indent=2)
    except IOError as e:
        pprint(f"[bright_red]Error saving state: {e}")


def load_state() -> dict:
    """
    Load application state from the state file.
    
    Returns:
        dict: The saved state data, or an empty dict if no state file exists
    """
    state_file_path = path.join(VAR_TO_DIR["CONFIG"], "state.json")
    
    if path.exists(state_file_path):
        try:
            with open(state_file_path, "r") as f:
                return ujson.load(f)
        except (ujson.JSONDecodeError, IOError) as e:
            pprint(f"[yellow]Warning: Could not load state file: {e}")
            return {}
    return {}
