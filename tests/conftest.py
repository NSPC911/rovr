import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from rovr.variables import maps

# Patch sys.__stdin__ early (before test collection imports application modules)
# so that textual_image skips terminal queries that require a real TTY.
logging.getLogger("textual_image._terminal").setLevel(logging.FATAL)
_stdin_patch = patch("sys.__stdin__", None)
_stdin_patch.start()


@pytest.fixture(autouse=True)
def isolate_test_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    monkeypatch.setitem(maps.VAR_TO_DIR, "CONFIG", config_dir.as_posix())
    monkeypatch.setattr("rovr.functions.pins.PIN_PATH", str(config_dir / "pins.json"))
