from pathlib import Path

import pytest
from textual.app import App
from textual.theme import Theme

from rovr.functions import themes as theme_utils


def test_extract_variable_declarations_ignores_nested_and_keeps_refs() -> None:
    css_text = """
    $primary: #88C0D0;
    $border-focused: $primary-lighten-3;

    Widget {
        $nested: should-not-be-picked-up;
        color: $primary;
    }
    """
    declared = theme_utils.extract_variable_declarations(css_text)
    assert declared == {
        "primary": "#88C0D0",
        "border-focused": "$primary-lighten-3",
    }


def test_extract_variable_declarations_ignores_commented_out_declarations() -> None:
    css_text = """
    $primary: #88C0D0;
    /*
    $primary: red;
    $secondary: also-ignored;
    */
    /* $accent: inline red; */
    """
    declared = theme_utils.extract_variable_declarations(css_text)
    assert declared == {"primary": "#88C0D0"}


def test_extract_variable_declarations_comment_brace_does_not_skew_depth() -> None:
    css_text = """
    /* a stray { in a comment */
    $primary: #88C0D0;
    """
    declared = theme_utils.extract_variable_declarations(css_text)
    assert declared == {"primary": "#88C0D0"}


def test_strip_variable_declarations_leaves_commented_declaration_untouched() -> None:
    css_text = (
        "$primary: #88C0D0;\n"
        "/*\n"
        "$primary: red;\n"
        "*/\n"
        "Widget {\n"
        "    color: $primary;\n"
        "}\n"
    )
    stripped = theme_utils.strip_variable_declarations(css_text)
    lines = stripped.splitlines()
    assert lines[0] == ""
    assert "$primary: red;" in stripped
    assert "Widget" in stripped


def test_parse_theme_file_ignores_commented_out_primary(tmp_path: Path) -> None:
    theme_file = tmp_path / "commented.tcss"
    theme_file.write_text("$primary: #88C0D0;\n/*\n$primary: #ff0000;\n*/\n")
    theme = theme_utils.parse_theme_file(theme_file)
    assert theme.primary == "#88C0D0"


def test_resolve_variable_references_chains_and_order_independence() -> None:
    declared = {"a": "$b", "b": "$c", "c": "final"}
    resolved = theme_utils.resolve_variable_references(declared, base={})
    assert resolved == {"a": "final", "b": "final", "c": "final"}


def test_resolve_variable_references_uses_base_for_unknown_names() -> None:
    declared = {"border-focused": "$primary-lighten-3"}
    base = {"primary-lighten-3": "#123456"}
    resolved = theme_utils.resolve_variable_references(declared, base)
    assert resolved == {"border-focused": "#123456"}


def test_resolve_variable_references_cycle_leaves_refs_in_place() -> None:
    declared = {"a": "$b", "b": "$a"}
    resolved = theme_utils.resolve_variable_references(declared, base={})
    # a cycle can never settle; it must not raise or infinite-loop
    assert resolved["a"].startswith("$")
    assert resolved["b"].startswith("$")


def test_pop_theme_field_overrides_extracts_known_fields() -> None:
    declared = {
        "primary": "#88C0D0",
        "dark": "true",
        "luminosity-spread": "0.2",
        "text-alpha": "not-a-float",
        "some-custom-var": "value",
    }
    fields = theme_utils.pop_theme_field_overrides(declared)
    assert fields == {
        "primary": "#88C0D0",
        "dark": True,
        "luminosity_spread": 0.2,
    }
    # matched names are removed from declared; unmatched/unparseable are kept
    assert declared == {
        "text-alpha": "not-a-float",
        "some-custom-var": "value",
    }


def test_pop_theme_field_overrides_skips_unresolved_color_refs() -> None:
    declared = {"primary": "$accent"}
    fields = theme_utils.pop_theme_field_overrides(declared)
    assert fields == {}
    # left behind as a plain variable rather than silently dropped
    assert declared == {"primary": "$accent"}


def test_parse_theme_file_requires_primary(tmp_path: Path) -> None:
    theme_file = tmp_path / "broken.tcss"
    theme_file.write_text("$secondary: #ffffff;\n")
    with pytest.raises(ValueError, match="primary"):
        theme_utils.parse_theme_file(theme_file)


def test_parse_theme_file_builds_theme_with_variables_and_css(tmp_path: Path) -> None:
    theme_file = tmp_path / "my-theme.tcss"
    theme_file.write_text(
        "$primary: #88C0D0;\n"
        "$dark: true;\n"
        "$accent-custom: #ff0000;\n"
        "\n"
        "Widget {\n"
        "    color: $accent-custom;\n"
        "}\n"
    )
    theme = theme_utils.parse_theme_file(theme_file)
    assert theme.name == "my-theme"
    assert theme.primary == "#88C0D0"
    assert theme.dark is True
    assert theme.variables == {"accent-custom": "#ff0000"}
    assert "Widget" in theme.css
    assert "color: $accent-custom;" in theme.css
    assert "$accent-custom: #ff0000;" not in theme.css
    assert "$primary: #88C0D0;" not in theme.css


def test_parse_theme_file_no_css_block_leaves_css_unset(tmp_path: Path) -> None:
    theme_file = tmp_path / "plain.tcss"
    theme_file.write_text("$primary: #88C0D0;\n")
    theme = theme_utils.parse_theme_file(theme_file)
    assert getattr(theme, "css", "") == ""


def test_parse_theme_file_bar_gradient(tmp_path: Path) -> None:
    theme_file = tmp_path / "gradients.tcss"
    theme_file.write_text(
        "$primary: #88C0D0;\n"
        "$bar-gradient-default: #111111 #222222;\n"
        "$bar-gradient-error: #ff0000 #990000;\n"
    )
    theme = theme_utils.parse_theme_file(theme_file)
    assert theme.bar_gradient == {
        "default": ["#111111", "#222222"],
        "error": ["#ff0000", "#990000"],
    }
    # bar-gradient declarations don't leak into the theme's plain variables
    assert "bar-gradient-default" not in theme.variables


def test_parse_theme_file_invalid_bar_gradient_color_raises(tmp_path: Path) -> None:
    theme_file = tmp_path / "bad-gradient.tcss"
    theme_file.write_text("$primary: #88C0D0;\n$bar-gradient-default: not-a-color;\n")
    with pytest.raises(Exception):  # noqa: B017 - Color.parse's own error type
        theme_utils.parse_theme_file(theme_file)


def test_theme_dirs_includes_user_theme_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from rovr.variables.maps import RovrVars

    monkeypatch.setattr(RovrVars, "ROVRTHEMES", (tmp_path / "themes").as_posix())
    dirs = theme_utils.theme_dirs()
    assert Path((tmp_path / "themes").as_posix()) in dirs


def test_theme_file_mtimes_snapshot_reflects_edits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from rovr.variables.maps import RovrVars

    user_themes = tmp_path / "themes"
    user_themes.mkdir()
    monkeypatch.setattr(RovrVars, "ROVRTHEMES", user_themes.as_posix())
    monkeypatch.setattr(
        theme_utils, "bundled_themes_path", tmp_path / "no-bundled-here"
    )

    theme_file = user_themes / "custom.tcss"
    theme_file.write_text("$primary: #88C0D0;\n")
    first = theme_utils.theme_file_mtimes()
    assert str(theme_file) in first

    theme_file.write_text("$primary: #ff0000;\n")
    theme_file.touch()
    second = theme_utils.theme_file_mtimes()
    assert second[str(theme_file)] >= first[str(theme_file)]


def test_register_all_themes_registers_valid_and_reports_broken(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from rovr.variables.maps import RovrVars

    user_themes = tmp_path / "themes"
    monkeypatch.setattr(RovrVars, "ROVRTHEMES", user_themes.as_posix())
    monkeypatch.setattr(
        theme_utils, "bundled_themes_path", tmp_path / "no-bundled-here"
    )

    (user_themes).mkdir(parents=True, exist_ok=True)
    (user_themes / "good.tcss").write_text("$primary: #88C0D0;\n")
    (user_themes / "broken.tcss").write_text("$secondary: #ffffff;\n")

    app = App()
    errors = theme_utils.register_all_themes(app)

    assert "good" in app.available_themes
    assert len(errors) == 1
    assert "broken.tcss" in errors[0]
    assert "primary" in errors[0]


def test_strip_variable_declarations_blanks_lines_but_keeps_line_count() -> None:
    css_text = "$primary: #88C0D0;\nWidget {\n    color: $primary;\n}\n"
    stripped = theme_utils.strip_variable_declarations(css_text)
    stripped_lines = stripped.splitlines()
    original_lines = css_text.splitlines()
    assert len(stripped_lines) == len(original_lines)
    assert stripped_lines[0] == ""
    assert "Widget" in stripped
    # the reference inside the rule is untouched, only the declaration line is blanked
    assert "color: $primary;" in stripped


def test_parse_theme_file_produces_a_real_theme_instance(tmp_path: Path) -> None:
    theme_file = tmp_path / "check.tcss"
    theme_file.write_text("$primary: #88C0D0;\n")
    theme = theme_utils.parse_theme_file(theme_file)
    assert isinstance(theme, Theme)
