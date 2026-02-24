from pathlib import Path

from rovr.functions.folder_prefs import set_folder_pref
from rovr.state_manager import StateManager


def test_apply_folder_sort_prefs_uses_custom_values(tmp_path: Path) -> None:
    target_folder = (tmp_path / "custom-sort").as_posix()
    set_folder_pref(target_folder, "extension", True)

    manager = StateManager()
    manager.apply_folder_sort_prefs(target_folder)

    assert manager.custom_sort_enabled is True
    assert manager.get_current_folder() == target_folder
    assert manager.sort_by == "extension"
    assert manager.sort_descending is True


def test_toggle_custom_sort_adds_and_removes_folder_pref(tmp_path: Path) -> None:
    target_folder = (tmp_path / "toggle-sort").as_posix()
    manager = StateManager()
    manager.apply_folder_sort_prefs(target_folder)

    assert manager.custom_sort_enabled is False
    manager.toggle_custom_sort()
    assert manager.custom_sort_enabled is True
    assert manager.get_sort_prefs(target_folder) == ("name", False)

    manager.toggle_custom_sort()
    assert manager.custom_sort_enabled is False
    assert manager.get_sort_prefs(target_folder) == ("name", False)
