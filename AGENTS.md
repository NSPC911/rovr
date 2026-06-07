# rovr - Agent Guidelines

a stylish, batteries-included terminal file manager built with Python and Textual.

## Build/Lint Commands

```bash
# Setup
uv sync --dev                      # Install all dependencies
prek install                       # Install pre-commit hooks (optional)

# Running
uv run rovr                        # Run the application
just run                           # Alias for uv run rovr
just dev                           # Run in dev mode with textual-dev console
just log                           # Launch textual console for debug output

# Code Quality
just check                         # Run all checks (ty + ruff)
  ty check                         # Type checking with ty
  ruff check                       # Linting

just format                        # Format code
just fmt                           # Alias for just format
  ruff check --unsafe-fixes --fix
  ruff format

# Testing
just test                          # Run tests with pytest
  just test tests/                 # Run all tests
  just test tests/test_clipboard.py # Run specific test file
  just test 4                      # Run with 4 parallel workers

# Building
just build                         # Build executable with Nuitka (onefile but can be customised)
just uv-build                      # Build wheel/sdist with uv

# Docs/Scripts
just gen-schema                    # Generate JSON schema for config
just gen-keys                      # Generate keybinds documentation
just typed                         # Convert schema to TypedDict
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
  However, do not just invoke `ruff check`, but rather run either `just format` or `just fmt` to apply fixes. Saves some tokens.

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

tests/
  test_*.py           # Test suite using pytest
  conftest.py         # Pytest configuration and fixtures
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
- **Formatting excludes**: `src/rovr/monkey_patches/sys_stdout.py`
- Use `uv` commands; do not use `pip` or `python -m`
- Always run `just check` before committing. Ruff may mention that certain errors are fixable; if so, run `just fmt` to apply fixes.

#### Tests
- Make sure to also run `just test` to ensure no tests are broken before committing.
- Keep in mind that the tests can be quite flaky at times. If an error occurs, just try again until it passes or 5 tries have been made. If it still fails after 5 tries, then there may be an actual issue that needs to be looked into.

#### multiprocessing.ProcessPoolExecutor and multiprocessing.Process notices
- Avoid creating a function in the same file as the `ProcessPoolExecutor` or `Process`.
  It is very likely that the file imports `rovr.variables.constants`, which checks in the global scope for the presence of `config`, and if not, re-loads the config, which can result to stdout being corrupted if the config has any issues
  For example of this, check out `src/rovr/functions/preview_workers.py` and its parent file `src/rovr/core/preview_container.py`

### Author preferences
- Avoid `if TYPE_CHECKING` blocks for imports; it looks bad
- Avoid adding unnecessary comments, aim for self-documenting code instead
- Commit with `NSPBot911 <176916861+NSPBot911@users.noreply.github.com>` to better distinguish between human and bot commits in the history.
  NEVER co-author with your provider (like `NSPBot911 <176916861+NSPBot911@users.noreply.github.com>` or `Claude Opus 4.6 <noreply@anthropic.com>`)
  You can, however, mention the provider used in the commit message, but you must use a syntax of `Used [Provider Name]: [Model Name]`

### Interesting Textual Patterns
- event handlers do not need to call their super() method. Textual implicitly handles this for you. If you don't want it to bubble to the super() method, call `prevent_default()` on the event.
- Using `subprocess.run(shell=True)` is completely allowed, there are no security implications to worry about since the user is always in control on the config and are the only ones that can run commands.
