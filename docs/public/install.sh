#!/usr/bin/env bash
set -euo pipefail

OS=$(uname -s)
case "$OS" in
    Linux)  os="linux" ;;
    Darwin) os="macos" ;;
    *)
        echo "Unsupported OS: $OS. Please use a Linux or macOS system." >&2
        exit 1
        ;;
esac

if [ -z "${ROVR_VERSION:-}" ]; then
    ROVR_VERSION=$(curl -fsSL "https://api.github.com/repos/NSPC911/rovr/releases/latest" | grep -o '"tag_name": *"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')
fi

release=$(curl -fsSL "https://api.github.com/repos/NSPC911/rovr/releases/tags/$ROVR_VERSION")
if echo "$release" | grep -q '"message": *"Not Found"'; then
    echo "Version $ROVR_VERSION does not exist." >&2
    exit 1
fi

INSTALL_PATH="$HOME/.local/share/rovr"
BIN_PATH="$HOME/.local/bin"

if [ -z "${ROVR_FORCE_REINSTALL:-}" ]; then
    echo "Checking for existing installation of rovr..."
    if [ -d "$INSTALL_PATH" ]; then
        OLD_EXE="$INSTALL_PATH/rovr.bin"
        if [ -f "$OLD_EXE" ]; then
            OLD_VER_NUM=$("$OLD_EXE" --version 2>/dev/null | awk 'NR==1{print $2}') || OLD_VER_NUM=""
            if [ -n "$OLD_VER_NUM" ]; then
                OLD_VER="v$OLD_VER_NUM"
                if [ "$OLD_VER" = "$ROVR_VERSION" ]; then
                    echo "Specified version $ROVR_VERSION is already installed at $INSTALL_PATH."
                    echo "Skipping installation."
                    exit 0
                fi
                NEWER=$(printf '%s\n' "$OLD_VER" "$ROVR_VERSION" | sort -V | tail -1)
                if [ "$NEWER" = "$OLD_VER" ]; then
                    echo "A newer version $OLD_VER is already installed at $INSTALL_PATH."
                    read -r -p "Are you sure you want to downgrade to $ROVR_VERSION? [y/N] " choice
                    case "$choice" in
                        [yY]) ;;
                        *)
                            echo "Keeping existing version $OLD_VER."
                            echo "Skipping installation."
                            exit 0
                            ;;
                    esac
                else
                    echo "An older version $OLD_VER is already installed at $INSTALL_PATH."
                    echo "Updating to $ROVR_VERSION..."
                    rm -rf "$INSTALL_PATH"
                fi
            fi
        fi
    fi
fi

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)        arch="x64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
        echo "Unsupported architecture: $ARCH." >&2
        exit 1
        ;;
esac

echo "Downloading rovr $ROVR_VERSION for $os $arch..."

DOWNLOAD_URL=$(echo "$release" | grep -o '"browser_download_url": *"[^"]*rovr-'"$os"'-'"$arch"'-nuitka\.zip"' | grep -o 'https://[^"]*')
if [ -z "$DOWNLOAD_URL" ]; then
    echo "No download found for rovr-$os-$arch-nuitka.zip in release $ROVR_VERSION." >&2
    exit 1
fi

mkdir -p "$INSTALL_PATH"
ZIP_PATH="$INSTALL_PATH/rovr.zip"
curl -fL -o "$ZIP_PATH" "$DOWNLOAD_URL"

echo "Extracting zip..."
unzip -q -o "$ZIP_PATH" -d "$INSTALL_PATH"
rm "$ZIP_PATH"
chmod +x "$INSTALL_PATH/rovr.bin"

mkdir -p "$BIN_PATH"
ln -sf "$INSTALL_PATH/rovr.bin" "$BIN_PATH/rovr"

echo "rovr $ROVR_VERSION has been installed to $INSTALL_PATH."

case "${SHELL:-}" in
    */zsh)
        RC="$HOME/.zshrc"
        PATH_LINE="export PATH=\"$BIN_PATH:\$PATH\""
        ;;
    */fish)
        RC="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
        PATH_LINE="fish_add_path \"$BIN_PATH\""
        ;;
    */xonsh)
        RC="$HOME/.xonshrc"
        PATH_LINE="\$PATH.insert(0, '$BIN_PATH')"
        ;;
    */tcsh)
        RC="$HOME/.tcshrc"
        PATH_LINE="setenv PATH \"$BIN_PATH:\$PATH\""
        ;;
    */csh)
        RC="$HOME/.cshrc"
        PATH_LINE="setenv PATH \"$BIN_PATH:\$PATH\""
        ;;
    */bash|*)
        RC="$HOME/.bashrc"
        PATH_LINE="export PATH=\"$BIN_PATH:\$PATH\""
        ;;
esac
if ! grep -qF "$BIN_PATH" "$RC" 2>/dev/null; then
    echo "Adding $BIN_PATH to PATH in $RC..."
    printf '\n%s\n' "$PATH_LINE" >> "$RC"
    echo "Restart your terminal or run 'source $RC' to apply."
fi

echo "Installation complete. You can now run 'rovr' from any terminal."
echo "Check out the the tutorial at https://nspc911.github.io/rovr/get-started/tutorial !"
