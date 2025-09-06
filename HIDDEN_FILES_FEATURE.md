# Hidden Files Toggle Feature (macOS Only)

## Overview
This feature allows macOS users to toggle the visibility of hidden files and folders (those starting with a dot `.`) in the Rovr file manager.

**Note: This feature is only available on macOS systems. On Windows and Linux, all files are always shown.**

## Key Binding
- **Ctrl+.** (Control + Period): Toggle hidden files visibility
  - Note: Textual recognizes this as `ctrl+full_stop` internally

## Configuration
The default visibility state can be configured in the `config.toml` file:

```toml
[settings]
show_hidden_files = false  # Set to true to show hidden files by default
```

The keybinding is configured as:
```toml
[keybinds]
toggle_hidden_files = ["ctrl+full_stop"]  # This responds to Ctrl+.
```

## How It Works

### Files Modified
1. **`src/rovr/config/config.toml`**: Added `show_hidden_files` setting and `toggle_hidden_files` keybinding
2. **`src/rovr/config/schema.json`**: Added schema definitions for the new setting and keybinding
3. **`src/rovr/functions/path.py`**: Modified `get_cwd_object()` function to accept a `show_hidden` parameter
4. **`src/rovr/core/file_list.py`**: 
   - Added `show_hidden_files` property to track state
   - Added `toggle_hidden_files()` method to toggle visibility
   - Modified `update_file_list()` to pass the setting to `get_cwd_object()`
5. **`src/rovr/app.py`**: Added key handler for the toggle keybinding

### Implementation Details

#### Path Filtering
The `get_cwd_object()` function in `path.py` now filters items during directory scanning:
```python
for item in listed_dir:
    # Skip hidden files if show_hidden is False
    if not show_hidden and item.name.startswith('.'):
        continue
```

#### State Management
The `FileList` class maintains the visibility state:
- Initialized from config on startup
- Toggled at runtime without affecting the config file
- Refreshes the file list when toggled

#### User Feedback
When toggling, users receive a notification showing the new state:
- "Hidden files are now shown"
- "Hidden files are now hidden"

## Usage Examples

### Default Behavior
By default, hidden files are not shown. The file list will only display regular files and folders.

### Toggling Visibility
1. While using Rovr, press `Ctrl+.` at any time
2. The file list will refresh immediately
3. A notification will confirm the new state
4. The setting persists for the current session

### Common Hidden Files/Folders
Examples of items affected by this toggle:
- `.git` - Git repository data
- `.gitignore` - Git ignore rules
- `.env` - Environment variables
- `.config` - Configuration directories
- `.ssh` - SSH keys directory
- `.bashrc`, `.zshrc` - Shell configuration files
- `.DS_Store` - macOS system files

## Testing
A test directory with sample hidden and visible files has been created at `test_hidden/` for verification:
- Visible items: `README.md`, `visible_file.txt`, `visible_folder/`, `normal_folder/`
- Hidden items: `.env`, `.gitignore`, `.hidden_file.txt`, `.git/`, `.config/`, `.hidden_folder/`

Run the test script to verify functionality:
```bash
python test_path_function.py
```

## Notes
- The toggle only affects the current session; it doesn't permanently change the config file
- The setting applies to all tabs in the current Rovr session
- Hidden files are sorted alphabetically along with visible files when shown
- Textual recognizes the Ctrl+. key combination as `ctrl+full_stop`, not `ctrl+period`