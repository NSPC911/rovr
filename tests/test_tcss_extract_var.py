from rovr.screens.theme_chooser import extract_var


def test_extract_var_basic() -> None:
    css = "$primary: red;\nBody { background: blue; }"
    assert extract_var("primary", css) == "red"


def test_extract_var_inline_selector() -> None:
    css = "$accent: #fff;Body{background:red}"
    assert extract_var("accent", css) == "#fff"


def test_extract_var_ignores_rule_block() -> None:
    css = "Body { $primary: red; }\n$primary: blue;"
    assert extract_var("primary", css) == "blue"


def test_extract_var_ignores_comments() -> None:
    css = "// $primary: red;\n$primary: blue;/* $primary: green; */"
    assert extract_var("primary", css) == "blue"


def test_extract_var_handles_strings_with_braces() -> None:
    css = '$primary: "{not a block}";\nBody{color:red}'
    assert extract_var("primary", css) == '"{not a block}"'


def test_extract_var_missing_returns_none() -> None:
    css = "Body { background: red; }"
    assert extract_var("missing", css) is None
