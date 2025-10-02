from humanize import naturalsize
from lzstring import LZString
from rich.console import Console
from textual.widget import Widget
from rovr.variables.maps import BORDER_BOTTOM

lzstring = LZString()
pprint = Console().print

def deep_merge(d: dict, u: dict) -> dict:
    """
    Deep merge two dictionaries (user config over template config).
    
    This is used to merge user configuration over template defaults,
    allowing users to override only specific settings while keeping
    all other defaults intact.
    
    Args:
        d: Base dictionary (template config)
        u: Update dictionary (user config)
        
    Returns:
        dict: Merged dictionary with user values taking precedence
    """
    for k, v in u.items():
        if isinstance(v, dict):
            # Recursively merge nested dictionaries
            d[k] = deep_merge(d.get(k, {}), v)
        else:
            # Direct assignment for non-dict values
            d[k] = v
    return d

def set_nested_value(d: dict, path_str: str, value: bool) -> None:
    """
    Set a value in a nested dictionary using dot notation (for CLI --with/--without flags).
    
    This allows users to enable/disable features via command line arguments
    like --with plugins.bat or --without interface.tooltips.
    
    Args:
        d: The config dictionary to modify
        path_str: Dot-separated path to the setting (e.g., "plugins.bat")
        value: The boolean value to set
    """
    keys = path_str.split(".")
    current = d
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            # We're at the final key - set the value
            try:
                if isinstance(current[key], dict) and "enabled" in current[key]:
                    # Handle feature objects with "enabled" property
                    current[key]["enabled"] = value
                elif type(current[key]) is type(value):
                    # Direct assignment for matching types
                    current[key] = value
                else:
                    # Type mismatch error
                    pprint("[bright_red underline]Config Error:[/]")
                    pprint(
                        f"[cyan bold]{path_str}[/]'s new value of type [cyan b]{type(value).__name__}[/] is not a [bold cyan]{type(current[key]).__name__}[/] type, and cannot be modified."
                    )
                    exit(1)
            except KeyError:
                # Path doesn't exist in config
                pprint("[bright_red underline]Config Error:[/]")
                pprint(
                    f"[cyan b]{path_str}[/] is not a valid path to an existing value and hence cannot be set."
                )
                exit(1)
        else:
            # Navigate deeper into the nested structure
            if not isinstance(current.get(key), dict):
                current[key] = {}
            current = current[key]

def set_scuffed_subtitle(element: Widget, *sections: str) -> None:
    border_bottom = BORDER_BOTTOM.get(
        element.styles.border_bottom[0], BORDER_BOTTOM["blank"]
    )
    subtitle = ""
    for index, section in enumerate(sections):
        subtitle += section
        if index + 1 != len(sections):
            subtitle += " "
            subtitle += (
                border_bottom if element.app.ansi_color else f"[r]{border_bottom}[/]"
            )
            subtitle += " "
    element.border_subtitle = subtitle

def natural_size(integer: int, suffix: str, filesize_decimals: int) -> str:
    assert suffix in ["decimal", "binary", "gnu"]
    match suffix:
        case "gnu":
            return naturalsize(
                value=integer,
                gnu=True,
                format=f"%.{filesize_decimals}f",
            )
        case "binary":
            return naturalsize(
                value=integer,
                binary=True,
                format=f"%.{filesize_decimals}f",
            )
        case _:
            return naturalsize(value=integer, format=f"%.{filesize_decimals}f")
