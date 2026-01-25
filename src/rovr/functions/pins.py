import os
from os import path
from typing import TypedDict, cast

import ujson

from rovr.variables.maps import (
    VAR_TO_DIR,
)

from .path import dump_exc, normalise

pins = {}


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
    tempins: PinsDict
    user_pins_file_path = path.join(VAR_TO_DIR["CONFIG"], "pins.json")

    # Ensure the user's config directory exists
    if not path.exists(VAR_TO_DIR["CONFIG"]):
        os.makedirs(VAR_TO_DIR["CONFIG"])
    if not path.exists(user_pins_file_path):
        tempins = {
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
        try:
            with open(user_pins_file_path, "w") as f:
                ujson.dump(tempins, f, escape_forward_slashes=False, indent=2)
        except IOError as exc:
            dump_exc(None, exc)

    try:
        with open(user_pins_file_path, "r") as f:
            loaded = ujson.load(f)
        if not isinstance(loaded, dict):
            raise ValueError()
        tempins = cast(PinsDict, loaded)
    except (IOError, ValueError, ujson.JSONDecodeError):
        # Reset pins on corrupt or something else happened
        tempins = {
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
    if "default" not in tempins or not isinstance(tempins["default"], list):
        tempins["default"] = [
            {"name": "Home", "path": "$HOME"},
            {"name": "Downloads", "path": "$DOWNLOADS"},
            {"name": "Documents", "path": "$DOCUMENTS"},
            {"name": "Desktop", "path": "$DESKTOP"},
            {"name": "Pictures", "path": "$PICTURES"},
            {"name": "Videos", "path": "$VIDEOS"},
            {"name": "Music", "path": "$MUSIC"},
        ]
    if "pins" not in tempins or not isinstance(tempins["pins"], list):
        tempins["pins"] = []

    for section_key in ["default", "pins"]:
        # again, screw you ty, `section_key` can never be unknown
        # but i dont know how to assert that to you
        for item in tempins[section_key]:  # ty: ignore[invalid-key]
            # no i will not use isinstance, ty screams at me
            # because of the replace code a few lines below
            if type(item) is dict and "path" in item and type(item["path"]) is str:
                # Expand variables
                for var, dir_path_val in VAR_TO_DIR.items():
                    item["path"] = item["path"].replace(f"${var}", dir_path_val)
                # Normalize to forward slashes
                item["path"] = normalise(item["path"])
    pins = tempins
    return tempins


def add_pin(pin_name: str, pin_path: str | bytes) -> None:
    """
    Add a pin to the pins file.

    Args:
        pin_name (str): Name of the pin.
        pin_path (str): Path of the pin.
    """
    global pins

    pins_to_write = ujson.loads(ujson.dumps(pins))

    pin_path_normalized = normalise(pin_path)
    pins_to_write.setdefault("pins", []).append({
        "name": pin_name,
        "path": pin_path_normalized,
    })

    sorted_vars = sorted(VAR_TO_DIR.items(), key=lambda x: len(x[1]), reverse=True)
    for section_key in ["default", "pins"]:
        if section_key in pins_to_write:
            for item in pins_to_write[section_key]:
                if (
                    isinstance(item, dict)
                    and "path" in item
                    and isinstance(item["path"], str)
                ):
                    for var, dir_path_val in sorted_vars:
                        item["path"] = item["path"].replace(dir_path_val, f"${var}")

    try:
        user_pins_file_path = path.join(VAR_TO_DIR["CONFIG"], "pins.json")
        with open(user_pins_file_path, "w") as f:
            ujson.dump(pins_to_write, f, escape_forward_slashes=False, indent=2)
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

    pins_to_write = ujson.loads(ujson.dumps(pins))

    pin_path_normalized = normalise(pin_path)
    if "pins" in pins_to_write:
        pins_to_write["pins"] = [
            pin
            for pin in pins_to_write["pins"]
            if not (isinstance(pin, dict) and pin.get("path") == pin_path_normalized)
        ]

    sorted_vars = sorted(VAR_TO_DIR.items(), key=lambda x: len(x[1]), reverse=True)
    for section_key in ["default", "pins"]:
        if section_key in pins_to_write:
            for item in pins_to_write[section_key]:
                if (
                    isinstance(item, dict)
                    and "path" in item
                    and isinstance(item["path"], str)
                ):
                    for var, dir_path_val in sorted_vars:
                        item["path"] = item["path"].replace(dir_path_val, f"${var}")

    try:
        user_pins_file_path = path.join(VAR_TO_DIR["CONFIG"], "pins.json")
        with open(user_pins_file_path, "w") as f:
            ujson.dump(pins_to_write, f, escape_forward_slashes=False, indent=2)
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
