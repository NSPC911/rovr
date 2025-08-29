# ROVR - Post-Modern Terminal File Explorer

**ALWAYS reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

ROVR is a Python TUI (Terminal User Interface) file explorer built with Textual. It provides a modern interface for navigating files and directories with advanced features like file previews, themes, and extensible configuration.

## Critical Requirements

**PYTHON VERSION**: This project requires Python 3.13. Do not attempt to build with older Python versions.

**UV DEPENDENCY MANAGER**: This project uses `uv` for dependency management and virtual environments. Install uv first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Working Effectively

### Bootstrap the Development Environment
ALWAYS run these commands in order to set up the development environment:

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Sync dependencies and create virtual environment**:
   ```bash
   uv sync
   ```
   **TIMING**: Takes 2-3 minutes on first run. NEVER CANCEL. Set timeout to 5+ minutes.

3. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

### Building and Running

#### Run the Application
```bash
# Production run
uv run poe run
# OR directly:
uv run rovr

# Development mode with hot reloading
uv run poe dev
```
**TIMING**: Application starts immediately (< 5 seconds). NEVER CANCEL.

#### Development and Debugging
```bash
# Run with debug console (separate terminal)
uv run poe log

# Run textual console for comprehensive debugging
uv run textual console
```

### Testing and Validation

**CRITICAL**: This project has NO formal test suite. Validation must be done manually.

#### Code Quality Checks
ALWAYS run these before committing changes:

```bash
# Format code (REQUIRED before commit)
uvx ruff format
# OR with uv:
uv run ruff format

# Lint code (REQUIRED before commit)  
uvx ruff check
# OR with uv:
uv run ruff check

# Type checking (REQUIRED before commit)
uvx ty check . --ignore unresolved-import
```

**TIMING**: Each command takes 10-30 seconds. NEVER CANCEL. Set timeout to 2+ minutes.

#### Pre-commit Validation
The project uses pre-commit hooks that run automatically:
```bash
# Test pre-commit hooks manually
uv run pre-commit run --all-files
```

### Manual Validation Scenarios

**MANDATORY**: After making changes, ALWAYS test these scenarios manually:

1. **Basic Application Launch**:
   ```bash
   uv run rovr
   ```
   - Verify the TUI loads without errors
   - Check that file navigation works
   - Test basic keyboard navigation (arrow keys, enter)

2. **Configuration Access**:
   ```bash
   uv run rovr --config-path
   ```
   - Verify config path is displayed correctly

3. **Version Check**:
   ```bash
   uv run rovr --version
   ```
   - Verify version is displayed

4. **Feature Toggles**:
   ```bash
   uv run rovr --with plugins.zen_mode
   uv run rovr --without interface.tooltips
   ```

5. **File Preview Testing**:
   - Navigate to different file types (.py, .md, .json, .toml)
   - Verify previews work correctly in the right panel
   - Test with/without `bat` command available
   - Test image preview functionality

6. **Screen/Modal Testing**:
   - Test file deletion modal (`src/rovr/screens/delete_files.py`)
   - Test permission modal (`src/rovr/screens/give_permission.py`)
   - Test input dialogs for file operations
   - Verify keyboard navigation works in modals

7. **Configuration Testing**:
   - Verify config loads from `~/.config/rovr/` (or platform equivalent)
   - Test theme switching functionality
   - Verify keybind customization works
   - Test plugin system (bat integration, zen mode)

## Documentation Development

The project includes comprehensive documentation built with Astro/Starlight:

### Documentation Commands
```bash
cd docs

# Install dependencies (first time)
pnpm install
# OR if pnpm not available:
npm install

# Development server
pnpm dev
# OR:
npm run dev
# Starts at localhost:4321

# Build production docs
pnpm build
# OR:
npm run build

# Preview production build
pnpm preview
# OR:
npm run preview
```

**TIMING**: 
- `npm install` or `pnpm install`: 1-2 minutes. NEVER CANCEL. Set timeout to 5+ minutes.
- `npm run dev` or `pnpm dev`: Starts in 10-20 seconds. 
- `npm run build` or `pnpm build`: 15-20 seconds. NEVER CANCEL. Set timeout to 2+ minutes.

### Generate JSON Schema
```bash
uv run poe gen-schema
```
Updates the configuration schema documentation.

## CI/CD and Deployment

### GitHub Actions Workflows

1. **Formatting Workflow** (`.github/workflows/formatting.yml`):
   - Runs on every push and PR
   - Validates code formatting with ruff
   - Runs type checking with ty
   
2. **Documentation Deployment** (`.github/workflows/deploy.yml`):
   - Deploys docs to GitHub Pages on releases
   - Uses pnpm to build Astro documentation

### Pre-commit Requirements
ALWAYS ensure your changes pass:
```bash
uv run pre-commit run --all-files
```

## Common Tasks Reference

The following are outputs from frequently run commands. Reference them instead of viewing, searching, or running bash commands to save time.

### Repository Root Structure
```
/home/runner/work/rovr/rovr
├── .git/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   │   ├── deploy.yml
│   │   └── formatting.yml
│   └── copilot-instructions.md
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version (contains: 3.13)
├── README.md
├── docs/ (Astro/Starlight documentation)
├── img/
├── package.json (legacy file)
├── pnpm-lock.yaml (legacy file) 
├── pyproject.toml (main project config)
├── requirements.txt (frozen dependencies)
├── src/
│   └── rovr/ (main Python package)
├── uv.lock
```

### Main Source Structure
```
src/rovr/
├── __init__.py
├── __main__.py (CLI entry point)
├── app.py (main application)
├── action_buttons/
├── config/ (configuration management)
│   ├── config.toml (default config)
│   ├── pins.json (pinned directories)
│   └── schema.json (config schema)
├── core/ (main TUI components)
│   ├── file_list.py
│   ├── pinned_sidebar.py
│   └── preview_container.py
├── screens/ (modal dialogs)
│   ├── delete_files.py
│   ├── give_permission.py
│   ├── input.py
│   └── _tester.py (development helper)
├── style.tcss (Textual CSS styling)
├── themes.py (theme system)
└── utils.py (utility functions)
```

### Key Configuration Outputs

#### pyproject.toml Summary
- **Build system**: hatchling
- **Python requirement**: >=3.13
- **Main dependencies**: textual, click, pillow, psutil
- **Dev dependencies**: ruff, commitizen, poethepoet, textual-dev
- **Scripts**: `rovr = "rovr.__main__:main"`

#### Pre-commit Configuration
- **Ruff formatting and linting** (auto-fix enabled)
- **Type checking with ty** (ignores unresolved-import)


## Repository Architecture
- `src/rovr/` - Main Python package
  - `src/rovr/app.py` - Main application entry point
  - `src/rovr/core/` - Core TUI components
  - `src/rovr/screens/` - Application screens/modals
  - `src/rovr/config/` - Configuration management
  - `src/rovr/themes.py` - Theme system
- `docs/` - Astro/Starlight documentation site
- `.github/workflows/` - CI/CD pipelines

### Important Files
- `pyproject.toml` - Project configuration, dependencies, and build settings
- `.pre-commit-config.yaml` - Code quality automation
- `src/rovr/style.tcss` - Textual CSS styling
- `requirements.txt` - Frozen dependencies (for reference)

## Common Development Tasks

### Adding New Features
1. Create feature branch
2. Make changes in `src/rovr/`
3. Update documentation if needed
4. Run validation commands:
   ```bash
   uvx ruff format
   uvx ruff check  
   uvx ty check . --ignore unresolved-import
   ```
5. Test manually with multiple scenarios
6. Commit with conventional commit format

### Adding Themes
1. Modify `src/rovr/themes.py`
2. Add theme assets if needed
3. Update theme documentation
4. Test theme switching functionality

### Configuration Changes
1. Modify configuration schema in `src/rovr/config/`
2. Regenerate schema: `uv run poe gen-schema`
3. Update documentation
4. Test configuration loading

### Development Helpers

The repository includes a modal testing helper:
```bash
# Test specific screens/modals during development
python src/rovr/screens/_tester.py
```
Edit `_tester.py` to test different modal screens by changing the screen name in the `push_screen` call.

## Troubleshooting

### Python Version Issues
- **CRITICAL**: Ensure Python 3.13 is installed and active
- Use `python --version` to verify
- If you have Python 3.12 or earlier, the build will fail with "requires a different Python: 3.12.x not in '>=3.13'"
- uv should automatically install and use the correct Python version
- **DO NOT** try to bypass the Python version requirement - it will cause import errors

### Import Errors
- Run `uv sync` to ensure all dependencies are installed
- Check that you're in the project root directory
- If `uv sync` fails with timeout errors, wait and retry - PyPI can be slow

### Network Issues
- If dependency installation fails with timeout errors, retry the command
- `uv sync` downloads many packages and may take longer on slow connections
- Consider increasing timeout values for `uv sync` to 10+ minutes on slow networks

### Formatting/Linting Failures
- Run `uvx ruff format` to auto-fix formatting
- Check `uvx ruff check` output for specific issues
- Most issues can be auto-fixed with `uvx ruff check --fix`

### TUI Display Issues
- Ensure terminal supports Unicode and colors
- Test with different terminal emulators
- Check font requirements (nerd fonts recommended)

## Performance Notes

**CRITICAL TIMING EXPECTATIONS**:
- Initial `uv sync`: 2-3 minutes
- Code formatting: 10-30 seconds
- Application startup: < 5 seconds
- Documentation build: 15-20 seconds
- Documentation install: 1-2 minutes

**NEVER CANCEL** any of these operations. Always set appropriate timeouts (2-5 minutes minimum).