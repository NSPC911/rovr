# rovr - Agent Guidelines

A post-modern terminal file explorer built with Python and Textual.

## Build/Lint Commands

```bash
# Setup
uv sync --dev                    # Install all dependencies
prek install                     # Install pre-commit hooks (optional)

# Running
uv run rovr                      # Run the application
poe run                          # Alias for uv run rovr
poe dev                          # Run in dev mode with textual-dev console
poe log                          # Launch textual console for debug output

# Code Quality
poe check                        # Run all checks (ty + ruff)
  ty check                       # Type checking with ty
  ruff check                     # Linting

poe format                       # Format code
poe fmt                          # Alias for poe format
  ruff check --unsafe-fixes --fix
  ruff format


# Building
poe build                        # Build executable with Nuitka (onefile but can be customised)
poe uv-build                     # Build wheel/sdist with uv

# Docs/Scripts
poe gen-schema                   # Generate JSON schema for config
poe gen-keys                     # Generate keybinds documentation
poe typed                        # Convert schema to TypedDict
```

## Code Style Guidelines

### General

- **Python**: 3.12+ required
- **Line length**: No strict limit (E501, W505 ignored)
- **Quotes**: Double quotes (`"`)
- **Indentation**: 4 spaces
- **Formatter**: ruff (not black)

### Imports

- Use **absolute imports only** (no relative imports)
- Example:

```python
from os import path
from typing import Callable

from rich.console import Console
from textual.app import App

from rovr.functions import icons
from rovr.classes.mixins import CheckboxRenderingMixin
```

- As for grouping or formatting, you can leave it to ruff.
  However, do not just invoke `ruff check`, but rather run either `poe format` or `poe fmt` to apply fixes. Saves some tokens.

### Type Annotations

- **Required**: All functions must have type annotations (ANN rules enforced)
- Use `ty` for type checking (not mypy)
- Common types: `str`, `int`, `bool`, `None`, `Callable`, `Iterable`, `Self`, `ClassVar`
- For Textual widgets, use proper types included in Textual.
- Do not however, make use of `if TYPE_CHECKING` blocks. It does not look good in the slightest (according to the author)

### Naming Conventions

- **Classes**: `CamelCase` (e.g., `FileList`, `Application`)
- **Functions/Variables**: `snake_case` (e.g., `get_filtered_dir_names`)
- **Constants**: UPPER_CASE (e.g., `MAX_ITEMS`)
- **Private**: Prefix with `_` (e.g., `_internal_helper`)

### Error Handling

- Use specific exceptions; avoid bare `except:`
- Custom exceptions in `rovr/classes/exceptions.py`
- Use `suppress` from contextlib for expected errors: (should be enforced by ruff)

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    path.unlink()
```

### Textual-Specific Patterns

- Inherit from Textual widgets with `inherit_bindings=False` for custom keybindings
- Use `@on(EventType)` decorators or `on_event` methods for event handling
- Use `@work` decorator for async background work (additional `thread=True` for blocking tasks)
- CSS files use `.tcss` extension, variables are defined with `$`, not all web CSS features are supported
- Widget composition in `compose()` methods
- For any widget modifications in a thread, use `call_from_thread` to run immediately as a block, or use `call_next`/`call_later`/`call_after_refresh` to send the function into the call stack.

### Project Structure

```
src/rovr/
  app.py              # Main Application class
  classes/            # Data classes, exceptions, mixins
  components/         # Reusable UI components
  core/               # Core widgets (FileList, etc.)
  functions/          # Utility functions
  screens/            # Screen classes
  variables/          # Constants and config
```

### Pre-commit Hooks

This project uses the new `prek` tool for pre-commit hooks. To run the check

```bash
prek # if available in system PATH
uv run prek # if installed as a dev dependency
```

- Runs ruff format and check
- Runs ty check

### Commit Convention

Follow Conventional Commits:

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Important Notes

- **Refactors discouraged**: The project prefers features over refactors
- **No tests**: This project does not have a test suite
- **Type checking excludes**: `src/rovr/classes/archive.py`
- **Formatting excludes**: `src/rovr/monkey_patches/sys_stdout.py`
- Use `uv` commands; do not use `pip` or `python -m`
- Always run `poe check` before committing
- There is no test suites. The author refuses to write tests and prefers to test manually.
