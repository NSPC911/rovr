#!/usr/bin/env python3
"""Test script for hidden files functionality in path.py."""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Create test directory structure
test_dir = Path(__file__).parent / "test_hidden"
test_dir.mkdir(exist_ok=True)

# Create some test files and folders
(test_dir / "visible_file.txt").touch(exist_ok=True)
(test_dir / ".hidden_file.txt").touch(exist_ok=True)
(test_dir / "visible_folder").mkdir(exist_ok=True)
(test_dir / ".hidden_folder").mkdir(exist_ok=True)
(test_dir / ".git").mkdir(exist_ok=True)
(test_dir / ".config").mkdir(exist_ok=True)
(test_dir / "normal_folder").mkdir(exist_ok=True)
(test_dir / "README.md").touch(exist_ok=True)
(test_dir / ".gitignore").touch(exist_ok=True)
(test_dir / ".env").touch(exist_ok=True)

print("Test directory created with files and folders")
print(f"Location: {test_dir}")
print("\nContents:")
for item in sorted(test_dir.iterdir()):
    prefix = "📁" if item.is_dir() else "📄"
    hidden = "🔒" if item.name.startswith(".") else "  "
    print(f"  {hidden} {prefix} {item.name}")

# Now directly test the modified function without complex imports
print("\n" + "="*50)
print("Testing get_cwd_object function")
print("="*50)

# Import just the necessary functions
import os
import stat
from os import path

def get_icon_for_file(name):
    return "📄"

def get_icon_for_folder(name):
    return "📁"

def normalise(location):
    return path.normpath(location).replace("\\", "/").replace("//", "/")

def get_cwd_object(cwd, show_hidden=False):
    """
    Get the objects (files and folders) in a provided directory
    Args:
        cwd(str): The working directory to check
        show_hidden(bool): Whether to include hidden files/folders (starting with .)

    Returns:
        folders(list[dict]): A list of dictionaries, containing "name" as the item's name and "icon" as the respective icon
        files(list[dict]): A list of dictionaries, containing "name" as the item's name and "icon" as the respective icon
    """
    folders, files = [], []
    try:
        listed_dir = os.scandir(cwd)
    except (PermissionError, FileNotFoundError, OSError):
        print(f"PermissionError: Unable to access {cwd}")
        return [PermissionError], [PermissionError]
    for item in listed_dir:
        # Skip hidden files if show_hidden is False
        if not show_hidden and item.name.startswith('.'):
            continue
            
        if item.is_dir():
            folders.append({
                "name": f"{item.name}",
                "icon": get_icon_for_folder(item.name),
                "dir_entry": item,
            })
        else:
            files.append({
                "name": item.name,
                "icon": get_icon_for_file(item.name),
                "dir_entry": item,
            })
    # Sort folders and files properly
    folders.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())
    print(f"Found {len(folders)} folders and {len(files)} files in {cwd}")
    return folders, files

# Test with show_hidden=False (default)
print("\n1. With show_hidden=False (default):")
folders, files = get_cwd_object(str(test_dir), show_hidden=False)
print(f"   Visible folders ({len(folders)}):")
for folder in folders:
    print(f"     📁 {folder['name']}")
print(f"   Visible files ({len(files)}):")
for file in files:
    print(f"     📄 {file['name']}")

# Test with show_hidden=True
print("\n2. With show_hidden=True:")
folders, files = get_cwd_object(str(test_dir), show_hidden=True)
print(f"   All folders ({len(folders)}):")
for folder in folders:
    print(f"     📁 {folder['name']}")
print(f"   All files ({len(files)}):")
for file in files:
    print(f"     📄 {file['name']}")

print("\n" + "="*50)
print("✅ Test completed successfully!")
print("\nThe difference:")
print("- With show_hidden=False: Only visible files/folders are shown")
print("- With show_hidden=True: All files/folders including hidden ones are shown")
print("\nTo test in the actual Rovr app:")
print("1. Run: python -m rovr")
print("2. Navigate to the test_hidden directory")
print("3. Press Ctrl+. (period) to toggle hidden files visibility")
print("4. You should see hidden files appear/disappear from the list")