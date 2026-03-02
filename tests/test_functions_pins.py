import json
from pathlib import Path

import pytest

import rovr.functions.pins as pins_module
from rovr.functions.pins import add_pin, load_pins, remove_pin, toggle_pin
from rovr.variables.maps import VAR_TO_DIR

DEFAULT_NAMES = {
    "Home",
    "Downloads",
    "Documents",
    "Desktop",
    "Pictures",
    "Videos",
    "Music",
}


@pytest.fixture(autouse=True)
def patch_pin_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pin_file = tmp_path / "pins.json"
    monkeypatch.setattr(pins_module, "PIN_PATH", str(pin_file))
    pins_module.pins = {}
    return pin_file


def test_load_pins_no_file_returns_defaults() -> None:
    result = load_pins()
    names = {item["name"] for item in result["default"]}
    assert names == DEFAULT_NAMES
    assert result["pins"] == []


def test_load_pins_valid_file_expands_home_variable() -> None:
    pin_file = Path(pins_module.PIN_PATH)
    data = {
        "default": [{"name": "Home", "path": "$HOME"}],
        "pins": [{"name": "My Dir", "path": "$HOME/mydir"}],
    }
    pin_file.write_text(json.dumps(data))

    result = load_pins()

    home = VAR_TO_DIR["HOME"]
    assert result["default"][0]["path"] == home
    assert result["pins"][0]["path"] == f"{home}/mydir"


def test_load_pins_corrupt_json_falls_back_to_defaults() -> None:
    Path(pins_module.PIN_PATH).write_text("{not valid json")

    result = load_pins()

    names = {item["name"] for item in result["default"]}
    assert names == DEFAULT_NAMES
    assert result["pins"] == []


def test_add_pin_appears_in_pins_and_persisted(tmp_path: Path) -> None:
    load_pins()
    target = tmp_path / "project"
    target.mkdir()
    target = target.as_posix()

    add_pin("Project", target)

    assert any(p.get("path") == target for p in pins_module.pins["pins"])
    saved = json.loads(Path(pins_module.PIN_PATH).read_text())
    assert any(p.get("name") == "Project" for p in saved["pins"])


def test_remove_pin_is_gone_from_pins(tmp_path: Path) -> None:
    load_pins()
    target = tmp_path / "to-remove"
    target.mkdir()
    target = target.as_posix()

    add_pin("ToRemove", target)
    assert any(p.get("path") == target for p in pins_module.pins["pins"])

    remove_pin(target)

    assert not any(p.get("path") == target for p in pins_module.pins["pins"])


def test_toggle_pin_adds_when_absent(tmp_path: Path) -> None:
    load_pins()
    target = tmp_path / "new-pin"
    target.mkdir()
    target = target.as_posix()

    assert not any(p.get("path") == target for p in pins_module.pins.get("pins", []))

    toggle_pin("New Pin", target)

    assert any(p.get("path") == target for p in pins_module.pins["pins"])


def test_toggle_pin_removes_when_present(tmp_path: Path) -> None:
    load_pins()
    target = tmp_path / "existing-pin"
    target.mkdir()
    target = target.as_posix()

    add_pin("Existing", target)
    assert any(p.get("path") == target for p in pins_module.pins["pins"])

    toggle_pin("Existing", target)

    assert not any(p.get("path") == target for p in pins_module.pins["pins"])
