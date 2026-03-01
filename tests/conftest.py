import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from rovr.variables import maps

logging.getLogger("textual_image._terminal").setLevel(logging.FATAL)


@pytest.fixture(scope="session", autouse=True)
def _patch_stdin() -> Iterator[None]:
    stdin_patch = patch("sys.__stdin__", None)
    stdin_patch.start()
    try:
        yield
    finally:
        stdin_patch.stop()


@pytest.fixture(autouse=True)
def isolate_test_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    monkeypatch.setitem(maps.VAR_TO_DIR, "CONFIG", config_dir.as_posix())  # ty: ignore
    monkeypatch.setattr("rovr.functions.pins.PIN_PATH", str(config_dir / "pins.json"))
