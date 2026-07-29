import sys

import pytest

from rovr.components.iterm2_image import _build_sequence, is_supported


class _Stdout:
    def __init__(self, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def test_build_sequence() -> None:
    assert _build_sequence("image", 100, 200) == (
        "\x1b]1337;File=inline=1;width=100px;height=200px;preserveAspectRatio=0:image\x07"
    )


@pytest.mark.parametrize("terminal", ["iTerm2", "WezTerm"])
def test_is_supported_for_iterm2_terminals(
    monkeypatch: pytest.MonkeyPatch, terminal: str
) -> None:
    monkeypatch.setattr(sys, "__stdout__", _Stdout(True))
    monkeypatch.setenv("TERM_PROGRAM", terminal)

    assert is_supported()


def test_is_supported_requires_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "__stdout__", _Stdout(False))
    monkeypatch.setenv("TERM_PROGRAM", "WezTerm")

    assert not is_supported()
