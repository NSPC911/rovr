import json
from pathlib import Path

import pytest

from rovr.functions import state


def test_save_and_load_ui_state(tmp_path, monkeypatch):
    # Redirect CONFIG dir to temp path
    cfg_dir = tmp_path / "config"
    monkeypatch.setitem(state.VAR_TO_DIR, "CONFIG", str(cfg_dir))

    # Ensure no state exists initially
    assert state.load_ui_state() == {}

    # Save a sample state
    sample = {"show_hidden_files": True, "footer_visible": False}
    state.save_ui_state(sample)

    # The file should exist
    p = Path(state.UI_STATE_FILENAME)
    assert p.exists()

    # Loading should include the saved keys
    loaded = state.load_ui_state()
    assert loaded.get("show_hidden_files") is True
    assert loaded.get("footer_visible") is False

