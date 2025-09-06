#!/bin/bash

# Script to remove macOS-only restrictions from Rovr hidden files feature
# Run this from your Rovr project directory: ~/Code/python/rovr

echo "Removing macOS-only restrictions from Rovr hidden files feature..."

# 1. Update app.py - remove platform check from keybinding
echo "Updating src/rovr/app.py..."

# Remove the platform.system() check from the keybinding
sed -i '' 's/case key if key in config\["keybinds"\]\["toggle_hidden_files"\] and platform.system() == "Darwin":/case key if key in config\["keybinds"\]\["toggle_hidden_files"\]:/' src/rovr/app.py

# Update the comment to remove macOS-only mention
sed -i '' 's/# toggle hidden files (macOS only)/# toggle hidden files/' src/rovr/app.py

# 2. Update file_list.py
echo "Updating src/rovr/core/file_list.py..."

# Replace the platform-specific initialization with the simple version
sed -i '' '/# Only enable hidden files toggle on macOS/,/else:/c\
        self.show_hidden_files = config.get("settings", {}).get("show_hidden_files", False)' src/rovr/core/file_list.py

# Remove the platform check from toggle_hidden_files method
# First, update the docstring
sed -i '' 's/"""Toggle the visibility of hidden files (macOS only)."""/"""Toggle the visibility of hidden files."""/' src/rovr/core/file_list.py

# Remove the platform check lines
sed -i '' '/if platform.system() != "Darwin":/,+2d' src/rovr/core/file_list.py

# 3. Update path.py
echo "Updating src/rovr/functions/path.py..."

# Remove the platform check from the hidden files filter
sed -i '' 's/if not show_hidden and item.name.startswith('\''.'\'') and platform.system() == "Darwin":/if not show_hidden and item.name.startswith('\''.'\''):/' src/rovr/functions/path.py

# Update the comment
sed -i '' 's/# Skip hidden files if show_hidden is False (macOS only)/# Skip hidden files if show_hidden is False/' src/rovr/functions/path.py

# 4. Update documentation if it exists
if [ -f "HIDDEN_FILES_FEATURE.md" ]; then
    echo "Updating HIDDEN_FILES_FEATURE.md..."
    
    # Remove macOS-only mentions from the title
    sed -i '' 's/# Hidden Files Toggle Feature (macOS Only)/# Hidden Files Toggle Feature/' HIDDEN_FILES_FEATURE.md
    
    # Update the overview
    sed -i '' 's/This feature allows macOS users to toggle/This feature allows users to toggle/' HIDDEN_FILES_FEATURE.md
    
    # Remove the macOS-only note
    sed -i '' '/\*\*Note: This feature is only available on macOS/d' HIDDEN_FILES_FEATURE.md
    
    # Remove the last line about non-macOS systems if it exists
    sed -i '' '/On non-macOS systems.*this feature is disabled/d' HIDDEN_FILES_FEATURE.md
fi

# 5. Optional: Clean up platform import if no longer needed
# Check if platform is still used in the files
echo "Checking if platform import is still needed..."

# For app.py - check if platform is used elsewhere
if ! grep -q "platform\." src/rovr/app.py | grep -v "^import platform"; then
    echo "  Removing unused platform import from app.py"
    sed -i '' '/^import platform$/d' src/rovr/app.py
fi

# For file_list.py - check if platform is used elsewhere
if ! grep -q "platform\." src/rovr/core/file_list.py | grep -v "^import platform"; then
    echo "  Removing unused platform import from file_list.py"
    sed -i '' '/^import platform$/d' src/rovr/core/file_list.py
fi

# Note: Keep platform import in path.py as it's used for other functions

echo ""
echo "✅ macOS-only restrictions removed successfully!"
echo ""
echo "The hidden files toggle feature now works on all operating systems:"
echo "  - Windows"
echo "  - macOS" 
echo "  - Linux"
echo ""
echo "You can now commit and push these changes:"
echo "  git add -A"
echo "  git commit -m 'Remove macOS-only restriction from hidden files toggle'"
echo "  git push"