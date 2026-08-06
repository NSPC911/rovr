from rich.console import Console
from rich.text import Text

from rovr.functions.ansi import ansi_to_rich_text


def assert_matches_rich(ansi: str) -> None:
    console = Console()
    expected = Text.from_ansi(ansi)
    actual = ansi_to_rich_text(ansi)

    assert actual.plain == expected.plain
    for offset in range(len(expected)):
        assert actual.get_style_at_offset(
            console, offset
        ) == expected.get_style_at_offset(console, offset)


def test_ansi_to_rich_text_parses_bat_truecolor_output() -> None:
    assert_matches_rich(
        "\x1b[38;2;216;222;233m  1\x1b[0m "
        "\x1b[38;2;129;161;193mfrom\x1b[0m\r\n"
        "\x1b[38;2;216;222;233m  2\x1b[0m\r\n"
    )


def test_ansi_to_rich_text_parses_colors_and_attributes() -> None:
    assert_matches_rich(
        "plain \x1b[1;31;44mbold\x1b[22;39;49m normal "
        "\x1b[38;5;200;48;2;1;2;3mextended\x1b[0m"
    )


def test_ansi_to_rich_text_parses_hyperlinks() -> None:
    text = ansi_to_rich_text(
        "\x1b]8;;https://example.com\x1b\\link\x1b]8;;\x1b\\ plain"
    )
    console = Console()

    assert text.plain == "link plain"
    assert text.get_style_at_offset(console, 0).link == "https://example.com"
    assert text.get_style_at_offset(console, 4).link is None
