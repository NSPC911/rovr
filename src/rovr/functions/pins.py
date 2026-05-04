import json
from copy import deepcopy
from os import makedirs, path
from typing import NotRequired, TypedDict, cast, Protocol
from pathlib import Path
import xml.etree.ElementTree as ET

from rovr.variables.maps import RovrVars
from rovr.variables.constants import config

from .path import dump_exc, normalise

pins = {}
PIN_PATH = path.join(RovrVars.ROVRCONFIG, "pins.json")
_places_providers = {}
_bookmarks_providers = {}

def _register(name, bucket):
    def decorator(cls):
        bucket[name] = cls
        return cls
    return decorator


def register_places(name):
    return _register(name, _places_providers)


def register_bookmarks(name):
    return _register(name, _bookmarks_providers)


class PinItem(TypedDict):
    name: str
    path: str
    icon: NotRequired[tuple[str, str]]


class PinsDict(TypedDict):
    default: list[PinItem]
    "The files to show in the default location"
    pins: list[PinItem]
    "Other added folders"


class PinProvider(Protocol):
    @classmethod
    def load_pins(cls) -> list[PinItem]: ...

    @classmethod
    def add_pin(cls, pin_name: str, pin_path: str | bytes) -> None: ...

    @classmethod
    def remove_pin(cls, pin_path: str | bytes) -> None: ...

    @classmethod
    def toggle_pin(cls, pin_name: str, pin_path: str) -> None: ...


@register_bookmarks("empty")
@register_places("empty")
class EmptyPinProvider():
    @classmethod
    def load_pins(cls) -> list[PinItem]:
        return []


@register_places("default")
class DefaultPlaces():

    @classmethod
    def load_pins(cls) -> list[PinItem]:
        return _sanitize([
            {"name": "Home", "path": "$HOME"},
            {"name": "Downloads", "path": "$DOWNLOADS"},
            {"name": "Documents", "path": "$DOCUMENTS"},
            {"name": "Desktop", "path": "$DESKTOP"},
            {"name": "Pictures", "path": "$PICTURES"},
            {"name": "Videos", "path": "$VIDEOS"},
            {"name": "Music", "path": "$MUSIC"},
        ])


@register_places("rovr")
class RovrPinedPlaces():

    @classmethod
    def load_pins(cls) -> list[PinItem]:
        try:
            places = []
            with open(PIN_PATH, "r") as f:
                loaded_pins = cast(PinsDict, json.load(f))
                # for place in loaded_pins["default"]:
                #     place["path"]=normalise(_expand_vars(place["path"]))
                #     places.append(place)
                places = _sanitize(loaded_pins["default"])
        except (IOError, ValueError, json.decoder.JSONDecodeError):
            places = DefaultPlaces.load_pins()
        return places


@register_bookmarks("rovr")
class RovrPinedBookmarks():

    @classmethod
    def load_pins(cls) -> list[PinItem]:
        try:
            bookmarks = []
            with open(PIN_PATH, "r") as f:
                loaded_pins = cast(PinsDict, json.load(f))
                # for bookmark in loaded_pins["pins"]:
                #     bookmark["path"]=normalise(_expand_vars(bookmark["path"]))
                #     bookmarks.append(bookmark)
                bookmarks = _sanitize(loaded_pins["pins"])
        except (IOError, ValueError, json.decoder.JSONDecodeError):
            bookmarks = []
        return bookmarks


@register_bookmarks("gtk")
class GTKBookmarks():
    bookmarks_path = "~/.config/gtk-3.0/bookmarks"

    @classmethod
    def load_pins(cls) -> list[PinItem]:
        bookmarks = []
        try:
            with open(cls.bookmarks_path) as bookmarks_file:
                for line in bookmarks_file.readlines():
                    try:
                        path, name = line.strip().split(" ", 1)
                        bookmarks.append({"name": name, "path": str(Path.from_uri(path))})
                    except ValueError:
                        pass
        except OSError:
            pass
        return bookmarks


@register_bookmarks("kde")
class KDEBookmarks():
    bookmarks_path = "~/.local/share/kfile/bookmarks.xml"

    @classmethod
    def load_pins(cls) -> list[PinItem]:
        bookmarks = []
        try:
            root = ET.parse(cls.bookmarks_path).getroot()
            for elem in root.iter("bookmark"):
                try:
                    title_elem = elem.find("title")
                    name = title_elem.text.strip()
                    path = str(Path.from_uri(elem.get("href", "").strip()))
                    bookmarks.append({"name": name, "path": path})
                except ValueError:
                    pass
        except OSError:
            pass

        return bookmarks

def _expand_vars(path: str) -> str:
    for var in RovrVars.slots:
        path = path.replace(f"${var}", getattr(RovrVars, var))
    return path


def _sanitize(pins: list[PinItem]) -> list[PinItem]:
    out = []
    for pin in pins:
        pin["path"] = normalise(_expand_vars(pin["path"]))
        out.append(pin)
    return out


def load_pins() -> PinsDict:
    _places = []
    _bookmarks = []

    for provider in config["interface"]["pins_places"]:
        _places.extend(_places_providers[provider].load_pins())
    for provider in config["interface"]["pins_bookmarks"]:
        _bookmarks.extend(_bookmarks_providers[provider].load_pins())

    return {
        "default": _places,
        "pins": _bookmarks,
    }


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
                    for var in RovrVars.slots:
                        item["path"] = item["path"].replace(
                            getattr(RovrVars, var), f"${var}"
                        )

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
    global pins

    pins_to_write = deepcopy(pins)

    pin_path_normalized = normalise(pin_path)
    if "pins" in pins_to_write:
        pins_to_write["pins"] = [
            pin
            for pin in pins_to_write["pins"]
            if not (isinstance(pin, dict) and pin.get("path") == pin_path_normalized)
        ]

    SORTED_VARS = sorted(vars(RovrVars).items(), key=lambda x: len(x[1]), reverse=True)
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
