from rovr.screens.theme_chooser import extract_var


def test_extract_var_basic() -> None:
    css = "$primary: red;\nBody { background: blue; }"
    assert extract_var(css) == {"primary": "red"}


def test_extract_var_inline_selector() -> None:
    css = "$accent: #fff;Body{background:red}"
    assert extract_var(css) == {"accent": "#fff"}


def test_extract_var_ignores_rule_block() -> None:
    css = "Body { $primary: red; }\n$primary: blue;"
    assert extract_var(css) == {"primary": "blue"}


def test_extract_var_ignores_comments() -> None:
    css = "// $primary: red;\n$primary: blue;/* $primary: green; */"
    assert extract_var(css) == {"primary": "blue"}


def test_extract_var_handles_strings_with_braces() -> None:
    css = '$primary: "{not a block}";\nBody{color:red}'
    assert extract_var(css) == {"primary": '"{not a block}"'}


def test_extract_var_missing_returns_none() -> None:
    css = "Body { background: red; }"
    assert extract_var(css) == {}


def test_extract_var_multiple_variables() -> None:
    css = "$primary: red;\n$accent: #fff;"
    assert extract_var(css) == {"primary": "red", "accent": "#fff"}
