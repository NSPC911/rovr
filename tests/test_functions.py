from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from rovr.functions import config, utils
from rovr.functions.path import normalise
from rovr.variables import constants


def test_deep_merge() -> None:
    old = {"a": 1, "b": {"c": 2, "d": 3}}
    new = {"b": {"c": 20, "e": 4}, "f": 5}
    expected = {"a": 1, "b": {"c": 20, "d": 3, "e": 4}, "f": 5}
    result = config.deep_merge(old, new)
    assert result == expected


def test_deep_merge_prepend_list() -> None:
    old = {"items": [1, 2, 3]}
    new = {"prepend_items": [0]}
    result = config.deep_merge(old, new)
    assert result == {"items": [0, 1, 2, 3]}
    assert "prepend_items" not in result


def test_deep_merge_append_list() -> None:
    old = {"items": [1, 2, 3]}
    new = {"append_items": [4]}
    result = config.deep_merge(old, new)
    assert result == {"items": [1, 2, 3, 4]}
    assert "append_items" not in result


def test_deep_merge_prepend_append_with_override() -> None:
    old = {"items": [1, 2, 3]}
    new = {"items": [10], "prepend_items": [0], "append_items": [99]}
    result = config.deep_merge(old, new)
    assert result == {"items": [0, 10, 99]}


def test_deep_merge_prepend_append_nested() -> None:
    old = {"section": {"items": ["a", "b"]}}
    new = {"section": {"prepend_items": ["z"], "append_items": ["c"]}}
    result = config.deep_merge(old, new)
    assert result == {"section": {"items": ["z", "a", "b", "c"]}}


def test_deep_merge_prepend_nonexistent_base_ignored() -> None:
    old = {"a": 1}
    new = {"prepend_missing": ["x"]}
    result = config.deep_merge(old, new)
    assert result == {"a": 1}
    assert "prepend_missing" not in result


def test_deep_merge_append_bool_key_untouched() -> None:
    old = {"append_new_tabs": True}
    new = {"append_new_tabs": False}
    result = config.deep_merge(old, new)
    assert result == {"append_new_tabs": False}


def test_load_keys_uses_nothing_without_user_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))

    keys = config.load_keys()

    assert keys == {}


def test_load_keys_user_file_is_standalone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))
    (tmp_path / "keys.toml").write_text('[global]\n"x" = "app.quit"\n')

    keys = config.load_keys()

    assert keys == {"global": {"x": {"action": "app.quit"}}}


def test_load_keys_can_inherit_preset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))
    (tmp_path / "keys.toml").write_text(
        'inherit = "sane"\n\n[global]\n"x" = "app.quit"\n'
    )

    keys = config.load_keys()

    assert keys["global"]["x"] == {"action": "app.quit"}
    assert isinstance(keys["lists"]["up"], dict)
    assert keys["lists"]["up"]["action"] == "cursor(-1)"


def test_load_keys_accepts_descriptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))
    (tmp_path / "keys.toml").write_text(
        '[global]\n"x" = { action = "app.quit", desc = "Quit" }\n'
    )

    keys = config.load_keys()

    assert keys == {"global": {"x": {"action": "app.quit", "desc": "Quit"}}}


def test_load_keys_replaces_inherited_binding_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))
    (tmp_path / "keys.toml").write_text(
        'inherit = "sane"\n\n[global]\n"ctrl+q" = { action = "custom_quit" }\n'
    )

    keys = config.load_keys()

    assert keys["global"]["ctrl+q"] == {"action": "custom_quit"}


def test_get_shortcut_uses_active_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        constants,
        "keys",
        {
            "delete_files": {
                "ctrl+d": {"action": "delete"},
                "D": {"action": "delete"},
                "x": {"action": "noop"},
                "y": {"y": {"action": "confirm"}},
            }
        },
    )

    assert utils.get_shortcut("delete_files", "delete") == "D"
    assert utils.get_shortcut("delete_files", "confirm") == "yy"
    assert utils.get_shortcut("delete_files", "cancel") == ""


def test_get_shortcut_falls_back_to_legacy_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(constants, "keys", {})

    assert utils.get_shortcut("paste_drop", "copy", "drag_and_drop") == "c"


def test_natural_size() -> None:
    assert utils.natural_size(1024, "binary", 2) == "1.00 KiB"
    assert utils.natural_size(1024, "decimal", 2) == "1.02 kB"
    assert utils.natural_size(1024, "gnu", 2) == "1.00K"
    assert utils.natural_size(123456789, "binary", 2) == "117.74 MiB"
    assert utils.natural_size(123456789, "decimal", 2) == "123.46 MB"
    assert utils.natural_size(123456789, "gnu", 2) == "117.74M"


@pytest.mark.asyncio
async def test_expand_command_tab_highlights(tmp_path: Path) -> None:
    directories = [
        normalise(str(tmp_path / name)) for name in ("first", "focused", "last")
    ]
    tabs = [
        SimpleNamespace(
            directory=directory,
            focus_on=None,
            session=SimpleNamespace(
                lastHighlighted={directory: {"name": f"file-{index}", "index": 0}}
            ),
        )
        for index, directory in enumerate(directories)
    ]
    highlighted = normalise(str(tmp_path / "focused" / "file-1"))
    app = SimpleNamespace(
        file_list=SimpleNamespace(
            highlighted_option=SimpleNamespace(
                dir_entry=SimpleNamespace(path=highlighted)
            ),
            get_selected_objects=_empty_selection,
        ),
        tabWidget=SimpleNamespace(active_tab=tabs[1], query=lambda _tab_type: tabs),
        query_one=lambda _selector: SimpleNamespace(selected=[]),
        notify=lambda *_args, **_kwargs: None,
    )

    result = await utils.expand_command(cast(Any, app), "%Th %T2h %th %t2h %trash")

    assert result == " ".join([
        normalise(str(tmp_path / "first" / "file-0")),
        normalise(str(tmp_path / "last" / "file-2")),
        normalise(str(tmp_path / "last" / "file-2")),
        normalise(str(tmp_path / "first" / "file-0")),
        "%trash",
    ])


async def _empty_selection() -> list[str]:
    return []
