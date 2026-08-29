from pathlib import Path

import pytest

from rovr.action_buttons import CopyButton
from rovr.action_buttons.sort_order import SortOrderButton
from rovr.app import Application
from rovr.classes.app_mixins import KeyHandler
from rovr.classes.textual_options import KeybindOption
from rovr.functions.config import load_keys, validate_keys
from rovr.navigation_widgets import PathInput
from rovr.screens import Dismissible, ScopedKeybinds
from rovr.screens.keybinds import ScopedKeybindList
from rovr.state_manager import StateManager

from .conftest import iter_until


def test_shorten_symbol_keys() -> None:
    assert {
        KeyHandler.shorten_key(key)
        for key in ("slash", "backslash", "at", "underscore", "minus", "plus")
    } == {"/", "\\", "@", "_", "-", "+"}


def test_validate_keys() -> None:
    assert not validate_keys({
        "main": {
            "+": {"action": "noop"},
            "ctrl+[": {"action": "cycle_tab(1)"},
            "shift+up": {"action": "noop"},
        },
        "path_input": {"A": {"action": "noop"}},
    })
    assert validate_keys({
        "unknown": {"ctrl+no_such_key": {"action": "noop"}},
        "main": {"shift+ctrl+a": {"action": "noop"}},
    }) == [
        "Unknown context [unknown]",
        'Invalid key "ctrl+no_such_key" in [unknown]',
        'Invalid key "shift+ctrl+a" in [main]',
    ]
    assert validate_keys({
        "file_list": {
            "Y": {
                "desc": "Copy",
                "y": {"action": "copy.to_rovr"},
                "ctrl+no_such_key": {"action": "noop"},
            }
        }
    }) == ['Invalid key "ctrl+no_such_key" in [file_list.Y]']


def test_load_key_chords(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROVR_CONFIG_FOLDER", str(tmp_path))
    (tmp_path / "keys.toml").write_text(
        '[main]\ng.x = "focus_file_list"\n'
        '[file_list.Y]\ndesc = "Copy"\n'
        'p = { action = "copy.highlighted", desc = "Copy path" }\n',
        encoding="utf-8",
    )

    keys = load_keys()
    chord = keys["file_list"]["Y"]
    assert isinstance(chord, dict)
    assert chord == {
        "desc": "Copy",
        "p": {"action": "copy.highlighted", "desc": "Copy path"},
    }
    assert keys["main"]["g"] == {"x": {"action": "focus_file_list"}}


@pytest.mark.asyncio
async def test_contextual_key_dispatch(tmp_path: Path) -> None:
    (tmp_path / "a").touch()
    (tmp_path / "b").touch()
    app = Application(startup_path=tmp_path.as_posix())
    app.keys = {"lists": {"j": {"action": "cursor(1)"}}}

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 2)
        app.file_list.focus()
        app.file_list.highlighted = 0

        assert [context for context, _ in app._active_key_contexts()] == [
            "file_list",
            "lists",
            "main",
        ]
        assert app._active_key_contexts()[-1] == ("main", app)
        assert app._key_namespaces()["file_list"] is app.file_list
        assert app._key_namespaces()["copy"] is app.query_one(CopyButton)
        assert app._key_namespaces()["sort_order"] is app.query_one(SortOrderButton)

        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.keys["lists"]["j"] = {"action": "noop"}
        await pilot.press("j")
        assert app.file_list.highlighted == 1

        app.keys["file_list"] = {"s": {"action": "sort_order.extension(True)"}}
        await pilot.press("s")
        assert app.query_one(StateManager).get_sort_prefs() == ("extension", True)

        state_manager = app.query_one(StateManager)
        pinned_sidebar_visible = state_manager.pinned_sidebar_visible
        app.keys = {"main": {"S": {"action": "toggle_pinned_sidebar"}}}
        await pilot.press("S")
        assert state_manager.pinned_sidebar_visible is not pinned_sidebar_visible

        app.push_screen(Dismissible("Modal"))
        await pilot.pause()
        assert "main" not in {context for context, _ in app._active_key_contexts()}


@pytest.mark.asyncio
async def test_input_consumes_printable_globals_and_uses_input_context(
    tmp_path: Path,
) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    app.keys = {
        "global": {"q": {"action": "app.quit"}},
        "inputs": {"backspace": {"action": "delete_left"}},
    }

    async with app.run_test(size=(143, 37)) as pilot:
        path_input = app.query_one(PathInput)
        path_input.value = "a"
        path_input.cursor_position = 1
        path_input.focus()

        await pilot.press("q")
        await pilot.pause()
        assert path_input.value == "aq"
        assert app.return_code is None

        await pilot.press("backspace")
        await pilot.pause()
        assert path_input.value == "a"


@pytest.mark.asyncio
async def test_scoped_keybinds_screen(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    app.keys = {
        "main": {
            "?": {"action": "show_keybinds", "desc": "Show keybindings"},
            "a": {
                "x": {"b": {"action": "focus_file_list", "desc": "Plain chord"}},
                "ctrl+x": {"action": "toggle_footer", "desc": "Modified chord"},
            },
        }
    }

    async with app.run_test(size=(143, 37)) as pilot:
        app.action_show_keybinds()
        await pilot.pause()

        assert isinstance(app.screen, ScopedKeybinds)
        option = app.screen.keybinds_list.options[1]
        assert isinstance(option, KeybindOption)
        assert "Show keybindings" in option.label
        labels = " ".join(
            str(option.label)
            for option in app.screen.keybinds_list.options
            if isinstance(option, KeybindOption)
        )
        assert "axb" in labels
        assert "a<ctrl+x>" in labels


@pytest.mark.asyncio
async def test_key_chords(tmp_path: Path) -> None:
    (tmp_path / "a").touch()
    (tmp_path / "b").touch()
    app = Application(startup_path=tmp_path.as_posix())
    app.keys = {
        "file_list": {
            "j": {"action": "cursor(1)"},
            "a": {
                "desc": "Move",
                "x": {"b": {"action": "cursor(1)", "desc": "Move down"}},
                "ctrl+x": {"action": "cursor(1)"},
                "n": {"action": "noop"},
            },
        }
    }

    async with app.run_test(size=(143, 37)) as pilot:
        await iter_until(pilot, lambda: app.file_list.option_count == 2)
        app.file_list.focus()
        app.file_list.highlighted = 0

        await pilot.press("a")
        popup = app.query_one("#key_chord")
        assert popup.display
        assert popup.border_title == "Move"
        await pilot.press("x", "b")
        assert app.file_list.highlighted == 1
        assert not popup.display

        app.file_list.highlighted = 0
        await pilot.press("a", "ctrl+x")
        assert app.file_list.highlighted == 1

        app.file_list.highlighted = 0
        await pilot.press("a", "escape")
        assert app.file_list.highlighted == 0
        assert not popup.display

        await pilot.press("a", "n")
        assert app.file_list.highlighted == 0
        assert not popup.display

        await pilot.press("a", "j")
        assert app.file_list.highlighted == 0
        assert not popup.display


def test_key_chord_display() -> None:
    assert ScopedKeybindList._format_sequence(("a", "x", "b")) == "axb"
    assert ScopedKeybindList._format_sequence(("a", "ctrl+x")) == "a<ctrl+x>"
