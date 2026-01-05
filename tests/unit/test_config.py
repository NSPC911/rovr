"""Unit tests for rovr.functions.config module."""

import contextlib
from unittest.mock import patch

import pytest


class TestGetVersion:
    """Tests for get_version function."""

    def test_returns_string(self) -> None:
        """Version is always a string."""
        from rovr.functions.config import get_version

        result = get_version()
        assert isinstance(result, str)

    def test_version_format(self) -> None:
        """Version follows semver-ish format or is 'master'."""
        from rovr.functions.config import get_version

        result = get_version()
        # Either a version number or "master"
        assert result == "master" or "." in result or result[0].isdigit()

    def test_package_not_found_fallback(self) -> None:
        """Returns 'master' when package not installed."""
        from importlib.metadata import PackageNotFoundError

        from rovr.functions.config import get_version

        with patch("rovr.functions.config.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()
            result = get_version()
            assert result == "master"


class TestTomlDump:
    """Tests for toml_dump error formatting."""

    def test_formats_error_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error messages are formatted with context."""
        import tomli

        from rovr.functions.config import toml_dump

        # Create a mock TOMLDecodeError
        doc = "key = 'value'\ninvalid syntax here\nmore = 'stuff'"
        exc = tomli.TOMLDecodeError(
            msg="Invalid value",
            doc=doc,
            pos=len("key = 'value'\n") + 5,  # Position in doc
        )

        # This function prints to console, so we just verify it doesn't crash
        # In a real test, we might capture output
        with contextlib.suppress(SystemExit):
            toml_dump("test.toml", exc)


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_config_is_valid_toml(self) -> None:
        """DEFAULT_CONFIG string is valid TOML."""
        import tomli

        from rovr.functions.config import DEFAULT_CONFIG

        # The DEFAULT_CONFIG has a placeholder, so we need to fill it
        config_str = DEFAULT_CONFIG.format(schema_url="https://example.com/schema.json")

        # Should parse without error
        parsed = tomli.loads(config_str)
        assert "theme" in parsed
        assert parsed["theme"]["default"] == "nord"
