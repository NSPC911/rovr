import contextlib
import json
from copy import deepcopy
from os import makedirs, path
from typing import NotRequired, TypedDict, cast

from rovr.variables.maps import RovrVars

from .path import dump_exc, normalise

pins = {}
raw_pins = {}
PIN_PATH = path.join(RovrVars.ROVRCONFIG, "pins.json")
TRASH = "$TRASH"
"""Special pin path that opens the recycle bin browser instead of a directory."""
cache = RovrVars.ROVRCACHE


class PinItem(TypedDict):
    name: str
    path: str
    icon: NotRequired[tuple[str, str]]


class PinsDict(TypedDict):
    default: list[PinItem]
    "The files to show in the default location"
    pins: list[PinItem]
    "Other added folders"


def _migrate_add_trash_pin(pins_dict: dict) -> None:
    """Inject the Trash pin into an existing pins.json exactly once.

    Guarded by a marker so a user who deliberately removes the Trash pin
    does not get it re-added on the next launch.
    """
    if path.exists(path.join(cache, "trash_pin_added")):
        return
    has_trash = any(
        isinstance(item, dict) and item.get("path") == TRASH
        for section in ("default", "pins")
        for item in pins_dict.get(section, [])
    )
    if not has_trash:
        pins_dict.setdefault("default", []).insert(
            1,
            {
                "name": "Trash",
                "path": TRASH,
            },
        )
        try:
            with open(PIN_PATH, "w") as f:
                json.dump(pins_dict, f, indent=2)
        except IOError as exc:
            dump_exc(None, exc)
    with contextlib.suppress(Exception):
        open(path.join(cache, "trash_pin_added"), "w").close()


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
    global pins, raw_pins
    _pins: PinsDict
    loaded_from_file = False

    if not path.exists(PIN_PATH):
        _pins = {
            "default": [
                {"name": "Home", "path": "$HOME"},
                {"name": "Trash", "path": TRASH},
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
            loaded_from_file = True
        except (IOError, ValueError, json.JSONDecodeError):
            # Reset pins on corrupt or something else happened
            _pins = {
                "default": [
                    {"name": "Home", "path": "$HOME"},
                    {"name": "Trash", "path": TRASH},
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
            {"name": "Trash", "path": TRASH},
            {"name": "Downloads", "path": "$DOWNLOADS"},
            {"name": "Documents", "path": "$DOCUMENTS"},
            {"name": "Desktop", "path": "$DESKTOP"},
            {"name": "Pictures", "path": "$PICTURES"},
            {"name": "Videos", "path": "$VIDEOS"},
            {"name": "Music", "path": "$MUSIC"},
        ]
    if "pins" not in _pins or not isinstance(_pins["pins"], list):
        _pins["pins"] = []

    if loaded_from_file:
        _migrate_add_trash_pin(cast(dict, _pins))

    # Keep an unexpanded copy so that add_pin/remove_pin can write existing
    # entries back exactly as they were, instead of re-deriving them from
    # the expanded form.
    raw_pins = deepcopy(_pins)

    for section_key in ("default", "pins"):
        for item in _pins[section_key]:
            if type(item) is dict and item.get("path") == TRASH:
                # Keep the sentinel intact so the sidebar can special-case it
                continue
            # no i will not use isinstance, ty screams at me
            # because of the replace code a few lines below
            if type(item) is dict and "path" in item and type(item["path"]) is str:
                # Expand variables
                for var in vars(RovrVars):
                    if var.startswith(("__", "ROVR")):
                        continue
                    item["path"] = item["path"].replace(
                        f"${var}", getattr(RovrVars, var)
                    )
                # Normalize to forward slashes
                item["path"] = normalise(str(item["path"]))
    pins = _pins
    return _pins


def add_pin(pin_name: str, pin_path: str | bytes) -> None:
    """
    Add a pin to the pins file.

    Args:
        pin_name (str): Name of the pin.
        pin_path (str): Path of the pin.

    Raises:
        FileNotFoundError: If the pin path does not exist.
        ValueError: If the pin path is a file, and not a folder.
    """

    if path.isfile(pin_path):
        raise ValueError(f"Expected a folder but got a file: {pin_path}")
    elif not path.exists(pin_path):
        raise FileNotFoundError(f"Path does not exist: {pin_path}")

    global raw_pins

    pins_to_write = deepcopy(raw_pins)

    pin_path_normalized = normalise(pin_path)
    pins_to_write.setdefault("pins", []).append({
        "name": pin_name,
        "path": pin_path_normalized,
    })

    if not path.exists(PIN_PATH):
        makedirs(path.dirname(PIN_PATH), exist_ok=True)

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
    global raw_pins

    pins_to_write = deepcopy(raw_pins)

    pin_path_normalized = normalise(pin_path)
    # `pins` (expanded) and `raw_pins` (as-written) share the same order,
    # since load_pins only mutates paths in place, never filters/reorders.
    if "pins" in pins_to_write and "pins" in pins:
        pins_to_write["pins"] = [
            raw_pin
            for raw_pin, expanded_pin in zip(pins_to_write["pins"], pins["pins"])
            if not (
                isinstance(expanded_pin, dict)
                and expanded_pin.get("path") == pin_path_normalized
            )
        ]

    try:
        with open(PIN_PATH, "w") as f:
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
