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
    for _ in range(int(timeout / interval)):
        await pilot.pause(interval)
        if method():
            return


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
    monkeypatch.setitem(maps.VAR_TO_DIR, "CONFIG", config_dir.as_posix())  # ty: ignore
    monkeypatch.setattr("rovr.functions.pins.PIN_PATH", str(config_dir / "pins.json"))
