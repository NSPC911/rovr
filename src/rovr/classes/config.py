from typing import Any

# The actual config types live in the generated `config.pyi` stub, which is read
# only by type checkers. At runtime the config is a plain dict, so any name
# imported from this module resolves to `Any` and costs nothing to load.
# Regenerate the stub with `poe typed`.


def __getattr__(name: str) -> Any:
    return Any
