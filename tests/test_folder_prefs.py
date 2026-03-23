import json
from pathlib import Path

from rovr.functions.folder_prefs import (
    get_folder_pref,
    has_folder_pref,
    load_folder_prefs,
    remove_folder_pref,
    set_folder_pref,
)
from rovr.variables.maps import RovrVars


def test_set_and_load_folder_preferences_round_trip(tmp_path: Path) -> None:
    target_folder = (tmp_path / "project").as_posix()
    set_folder_pref(target_folder, "size", True)

    assert has_folder_pref(target_folder)
    assert get_folder_pref(target_folder) == {
        "sort_by": "size",
        "sort_descending": True,
    }

    loaded = load_folder_prefs()
    assert loaded[target_folder] == {
        "sort_by": "size",
        "sort_descending": True,
    }


def test_remove_folder_preference_updates_state(tmp_path: Path) -> None:
    target_folder = (tmp_path / "to-remove").as_posix()
    set_folder_pref(target_folder, "name", False)
    remove_folder_pref(target_folder)

    assert not has_folder_pref(target_folder)
    assert get_folder_pref(target_folder) is None


def test_load_folder_prefs_expands_variable_paths() -> None:
    folder_path = Path(RovrVars.ROVRCONFIG)
    if not folder_path.exists():
        folder_path.mkdir(parents=True)
    prefs_file = folder_path / "folder_preferences.json"
    with open(prefs_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "$HOME/fixture": {
                    "sort_by": "natural",
                    "sort_descending": False,
                }
            },
            file,
        )

    loaded = load_folder_prefs()
    assert f"{RovrVars.HOME}/fixture" in loaded
