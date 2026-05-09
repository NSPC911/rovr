import json
from copy import deepcopy
from os import path
from typing import TypedDict, cast

from rovr.variables.maps import SORTED_VARS, VAR_TO_DIR

from .path import dump_exc, normalise

pins = {}
PIN_PATH = path.join(VAR_TO_DIR["CONFIG"], "pins.json")


class PinsDict(TypedDict):
    default: list[dict[str, str | list[str]]]
    "The files to show in the default location"
    pins: list[dict[str, str | list[str]]]
    "Other added folders"


def load_pins() -> PinsDict:
    """
    Load the pinned files from a JSON file in the user's config directory.
    Returns:
        dict: A dictionary with the default values, and the custom added pins.
    Raises:
        ValueError: If the config is of the wrong type
    """
    # I'm not entirely sure why the pins break when
    # pins isn't set global, I can't be bothered for now
    # until an issue gets raised in the future
    global pins
    _pins: PinsDict

    if not path.exists(PIN_PATH):
        _pins = {
            "default": [
                {"name": "Home", "path": "$HOME"},
                {"name": "Downloads", "path": "$DOWNLOADS"},
                {"name": "Documents", "path": "$DOCUMENTS"},
                {"name": "Desktop", "path": "$DESKTOP"},
                {"name": "Pictures", "path": "$PICTURES"},
                {"name": "Videos", "path": "$VIDEOS"},
                {"name": "Music", "path": "$MUSIC"},
            ],
            "pins": [],
        }
    else:
        try:
            with open(PIN_PATH, "r") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                raise ValueError()
            _pins = cast(PinsDict, loaded)
        except (IOError, ValueError, json.JSONDecodeError):
            # Reset pins on corrupt or something else happened
            _pins = {
                "default": [
                    {"name": "Home", "path": "$HOME"},
                    {"name": "Downloads", "path": "$DOWNLOADS"},
                    {"name": "Documents", "path": "$DOCUMENTS"},
                    {"name": "Desktop", "path": "$DESKTOP"},
                    {"name": "Pictures", "path": "$PICTURES"},
                    {"name": "Videos", "path": "$VIDEOS"},
                    {"name": "Music", "path": "$MUSIC"},
                ],
                "pins": [],
            }

    # If list died
    if "default" not in _pins or not isinstance(_pins["default"], list):
        _pins["default"] = [
            {"name": "Home", "path": "$HOME"},
            {"name": "Downloads", "path": "$DOWNLOADS"},
            {"name": "Documents", "path": "$DOCUMENTS"},
            {"name": "Desktop", "path": "$DESKTOP"},
            {"name": "Pictures", "path": "$PICTURES"},
            {"name": "Videos", "path": "$VIDEOS"},
            {"name": "Music", "path": "$MUSIC"},
        ]
    if "pins" not in _pins or not isinstance(_pins["pins"], list):
        _pins["pins"] = []

    for section_key in ["default", "pins"]:
        # again, screw you ty, `section_key` can never be unknown
        # but i dont know how to assert that to you
        for item in _pins[section_key]:  # ty: ignore[invalid-key]
            # no i will not use isinstance, ty screams at me
            # because of the replace code a few lines below
            if type(item) is dict and "path" in item and type(item["path"]) is str:
                # Expand variables
                for var, dir_path_val in VAR_TO_DIR.items():
                    item["path"] = item["path"].replace(f"${var}", dir_path_val)
                # Normalize to forward slashes
                item["path"] = normalise(item["path"])
    pins = _pins
    return _pins


def add_pin(pin_name: str, pin_path: str | bytes) -> None:
    """
    Add a pin to the pins file.

    Args:
        pin_name (str): Name of the pin.
        pin_path (str): Path of the pin.
    """
    global pins

    pins_to_write = deepcopy(pins)

    pin_path_normalized = normalise(pin_path)
    pins_to_write.setdefault("pins", []).append({
        "name": pin_name,
        "path": pin_path_normalized,
    })

    for section_key in ["default", "pins"]:
        if section_key in pins_to_write:
            for item in pins_to_write[section_key]:
                if (
                    isinstance(item, dict)
                    and "path" in item
                    and isinstance(item["path"], str)
                ):
                    for var, dir_path_val in SORTED_VARS:
                        item["path"] = item["path"].replace(dir_path_val, f"${var}")

    try:
        with open(PIN_PATH, "w") as f:
            json.dump(pins_to_write, f, indent=2)
    except IOError as exc:
        dump_exc(None, exc)

    load_pins()


def remove_pin(pin_path: str | bytes) -> None:
    """
    Remove a pin from the pins file.

    Args:
        pin_path (str): Path of the pin to remove.
    """
    global pins

    pins_to_write = deepcopy(pins)

    pin_path_normalized = normalise(pin_path)
    if "pins" in pins_to_write:
        pins_to_write["pins"] = [
            pin
            for pin in pins_to_write["pins"]
            if not (isinstance(pin, dict) and pin.get("path") == pin_path_normalized)
        ]

    SORTED_VARS = sorted(VAR_TO_DIR.items(), key=lambda x: len(x[1]), reverse=True)
    for section_key in ["default", "pins"]:
        if section_key in pins_to_write:
            for item in pins_to_write[section_key]:
                if (
                    isinstance(item, dict)
                    and "path" in item
                    and isinstance(item["path"], str)
                ):
                    for var, dir_path_val in SORTED_VARS:
                        item["path"] = item["path"].replace(dir_path_val, f"${var}")

    try:
        with open(pin_path, "w") as f:
            json.dump(pins_to_write, f, indent=2)
    except IOError as exc:
        dump_exc(None, exc)

    load_pins()  # Reload


def toggle_pin(pin_name: str, pin_path: str) -> None:
    """
    Toggle a pin in the pins file. If it exists, remove it; if not, add it.

    Args:
        pin_name (str): Name of the pin.
        pin_path (str): Path of the pin.
    """
    pin_path_normalized = normalise(pin_path)

    pin_exists = False
    if "pins" in pins:
        for pin_item in pins["pins"]:
            if (
                isinstance(pin_item, dict)
                and pin_item.get("path") == pin_path_normalized
            ):
                pin_exists = True
                break

    if pin_exists:
        remove_pin(pin_path_normalized)
    else:
        add_pin(pin_name, pin_path_normalized)
