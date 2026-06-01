#!/usr/bin/env bash
set -euo pipefail

OS=$(uname -s)
case "$OS" in
    Linux)  os="linux" ;;
    Darwin) os="macos" ;;
    *)
        echo "Bro." >&2
        exit 1
        ;;
esac


INSTALL_PATH="$HOME/.local/share/rovr"
BIN_LINK="$HOME/.local/bin/rovr"

if [ ! -d "$INSTALL_PATH" ] && [ ! -e "$BIN_LINK" ]; then
    echo "rovr is not installed."
    exit 0
fi

if [ ! -d "$INSTALL_PATH" ]; then
    echo "Installation directory not found at $INSTALL_PATH."
    exit 0
else
    echo "Found rovr installation at $INSTALL_PATH."
fi

if [ -e "$BIN_LINK" ]; then
    VER_NUM=$("$BIN_LINK" --version 2>/dev/null | awk 'NR==1{print $2}') || VER_NUM="unknown"
    echo "Found rovr v$VER_NUM installed."
fi

read -r -p "Are you sure you want to uninstall rovr? [y/N] " choice </dev/tty
case "$choice" in
    [yY]) ;;
    *)
        echo "Uninstallation cancelled."
        exit 0
        ;;
esac

if [ -d "$INSTALL_PATH" ]; then
    echo "Removing $INSTALL_PATH..."
    rm -rf "$INSTALL_PATH"
fi

if [ -e "$BIN_LINK" ] || [ -L "$BIN_LINK" ]; then
    echo "Removing $BIN_LINK..."
    rm -f "$BIN_LINK"
fi

echo "rovr has been uninstalled successfully."
echo "Note: PATH entries added during installation were not removed. You may manually clean up your shell configuration files if desired."
