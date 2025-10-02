import os
from os import path
from typing import Optional
import jsonschema
import toml
import ujson
from lzstring import LZString
from rich.console import Console
from rovr.functions.utils import deep_merge
from rovr.variables.maps import VAR_TO_DIR

lzstring = LZString()
pprint = Console().print

def load_config(config_path: Optional[str] = None) -> dict:
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    default_user_config_path = path.join(VAR_TO_DIR["CONFIG"], "config.toml")
    if not path.exists(default_user_config_path):
        with open(default_user_config_path, "w") as file:
            file.write(
                '#:schema  https://raw.githubusercontent.com/NSPC911/rovr/refs/heads/master/src/rovr/config/schema.json\n[theme]\ndefault = "nord"'
            )

    with open(path.join(path.dirname(__file__), "../config/config.toml"), "r") as f:
        try:
            template_config = toml.loads(f.read())
        except toml.decoder.TomlDecodeError as e:
            pprint(f"[bright_red]Template Config TOML Syntax Error:\n    {e}")
            exit(1)

    user_config_path = config_path if config_path else default_user_config_path
    user_config = {}
    if path.exists(user_config_path):
        with open(user_config_path, "r") as f:
            user_config_content = f.read()
            if user_config_content:
                try:
                    user_config = toml.loads(user_config_content)
                except toml.decoder.TomlDecodeError as e:
                    pprint(f"[bright_red]User Config TOML Syntax Error in {user_config_path}:\n    {e}")
                    exit(1)
    elif config_path:
        pprint(f"[yellow]Warning: Custom config file not found: {config_path}[/yellow]")
        pprint("[yellow]Using default configuration.[/yellow]")

    config = deep_merge(template_config, user_config)

    with open(path.join(path.dirname(__file__), "../config/schema.json"), "r") as f:
        schema = ujson.load(f)

    def add_required_recursively(node: dict) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node and "required" not in node:
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

    if config["settings"]["image_protocol"] == "Auto":
        config["settings"]["image_protocol"] = ""
    return config


def config_setup() -> None:
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    if not path.exists(path.join(VAR_TO_DIR["CONFIG"], "style.tcss")):
        with open(path.join(VAR_TO_DIR["CONFIG"], "style.tcss"), "a") as _:
            pass
