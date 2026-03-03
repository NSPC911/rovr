import logging
from pathlib import Path
from typing import Callable
from unittest.mock import patch

import pytest
from textual.pilot import Pilot

from rovr.variables import maps


async def iter_until(
    pilot: Pilot,
    method: Callable[[], bool],
    timeout: float = 2.0,
    interval: float = 0.1,
) -> None:
    """Helper function to repeatedly call a method until it returns True or a timeout is reached.
     Args:
        pilot: The Pilot instance to use for pausing between calls.
        method: A callable that returns a boolean indicating whether the desired condition is met.
        timeout: The maximum time to wait for the condition to be met, in seconds.
        interval: The time to wait between calls to the method, in seconds.

    Raises:
        AssertionError: If the method does not return True within the specified timeout.
    """  # noqa: DOC502
    for _ in range(int(timeout / interval)):
        await pilot.pause(interval)
        if method():
            return
    assert method()


# Patch sys.__stdin__ early (before test collection imports application modules)
# so that textual_image skips terminal queries that require a real TTY.
# also no, i cannot use pytest fixures because the import of textual_image happens
# before the test even runs, so the patch has to be global and outside of any function.
logging.getLogger("textual_image._terminal").setLevel(logging.FATAL)
_stdin_patch = patch("sys.__stdin__", None)
_stdin_patch.start()


@pytest.fixture(autouse=True)
def isolate_test_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    # ensure cd
    monkeypatch.chdir(tmp_path)
    # reset
    monkeypatch.setattr("rovr.functions.pins.pins", {})
    monkeypatch.setattr("rovr.functions.folder_prefs.folder_prefs", {})

    monkeypatch.setitem(maps.VAR_TO_DIR, "CONFIG", config_dir.as_posix())  # ty: ignore
    monkeypatch.setattr("rovr.functions.pins.PIN_PATH", str(config_dir / "pins.json"))
