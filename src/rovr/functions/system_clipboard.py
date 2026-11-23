# Copyright (c) 2026 NSPC911
# Licensed under the MIT License.
#
# You are free to copy, paste, and modify this file in your own projects,
# provided that this copyright notice and attribution remain intact.

# with reference from https://gitee.com/DreamMaoMao/clipboard.yazi for the wayland and x11 side
# macOS uses osascript thanks to https://codeberg.org/deppes/yazi-plugins/src/branch/main/system-clipboard.yazi
# windows is modified from clipboard.yazi but made slightly safer

import asyncio
import base64
import platform
import shutil
from os import path
from pathlib import Path
from subprocess import CompletedProcess


class ClipboardError(Exception):
    pass


class ClipboardToolNotFoundError(ClipboardError):
    def __init__(self, tool: str, platform: str, hint: str | None = None) -> None:
        self.tool = tool
        self.platform = platform
        self.hint = hint
        message = f"Clipboard tool '{tool}' not found on {platform}"
        if hint:
            message += f". {hint}"
        super().__init__(message)


class ClipboardCommandError(ClipboardError):
    def __init__(self, tool: str, return_code: int, stderr: str | None = None) -> None:
        self.tool = tool
        self.return_code = return_code
        self.stderr = stderr
        message = f"Clipboard command '{tool}' failed with exit code {return_code}"
        if stderr and stderr.strip():
            message += f": {stderr.strip()}"
        super().__init__(message)


async def copy_files_to_system_clipboard(
    paths: list[str],
) -> bool | Exception:
    """Copy file paths to the system clipboard.

    Args:
        paths: List of file paths to copy.

    Returns:
        True if successful, or an Exception if something went wrong.
    """
    system = platform.system()
    try:
        if system == "Windows":
            output = await _copy_windows(paths)
        elif system == "Darwin":
            output = await _copy_macos(paths)
        elif system == "Linux":
            output = await _copy_linux(paths)
        else:
            return ClipboardError(f"Unsupported platform: {system}")

        if output is None or output.returncode == 0:
            return True
        else:
            tool = output.args[0] if output.args else "unknown"
            return ClipboardCommandError(tool, output.returncode, output.stderr)
    except Exception as exc:
        return exc


async def _copy_windows(paths: list[str]) -> CompletedProcess | None:
    if not paths:
        return None

    if not shutil.which("powershell"):
        raise ClipboardToolNotFoundError(
            "powershell", "Windows", "PowerShell should be available on Windows"
        )

    abs_paths = "\n".join(
        base64.b64encode(path.abspath(p).encode("utf-8")).decode("ascii") for p in paths
    ).encode("ascii")

    command = [
        "powershell",
        "-NoProfile",
        "-NoLogo",
        "-NonInteractive",
        "-Command",
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$data = [System.Collections.Specialized.StringCollection]::new(); "
        "$lines = @($input | Where-Object { $_ -ne '' } | "
        "ForEach-Object { [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_)) }); "
        "if ($lines.Count -gt 0) { "
        "  $data.AddRange([string[]]$lines); "
        "  [System.Windows.Forms.Clipboard]::SetFileDropList($data) "
        "}",
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=abs_paths), timeout=5
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        exc.add_note("powershell clipboard command timed out")
        raise exc from None
    return CompletedProcess(
        args=command,
        returncode=process.returncode or 0,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
    )


async def _copy_macos(paths: list[str]) -> CompletedProcess | None:
    if not paths:
        return None

    script = (
        "on run argv\n"
        "  set fileList to {}\n"
        "  repeat with p in argv\n"
        "    set end of fileList to POSIX file p\n"
        "  end repeat\n"
        "  set the clipboard to fileList\n"
        "end run"
    )
    command = ["osascript", "-e", script, *[str(Path(p).resolve()) for p in paths]]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        exc.add_note("osascript clipboard command timed out")
        raise exc from None
    return CompletedProcess(
        args=command,
        returncode=process.returncode or 0,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
    )


async def _copy_linux(paths: list[str]) -> CompletedProcess | None:
    from os import environ

    if not paths:
        return None

    # Try wl-copy first (Wayland)
    if environ.get("XDG_SESSION_TYPE") == "wayland" and shutil.which("wl-copy"):
        command = ["wl-copy", "--type", "text/uri-list", "--"] + [
            f"{Path(path).resolve().as_uri()}\n" for path in paths
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            # quite weird, the issue with this is that
            # i must not pipe wl-copy's stderr/&2 stream
            # to null, so im forced to leave stderr open
            # hopefully it doesnt cause issues...
            # # stderr=asyncio.subprocess.STDOUT,
        )
        stdin = None
        using = "wl-copy"
    # Fall back to xclip (X11)
    elif environ.get("XDG_SESSION_TYPE") == "x11" and shutil.which("xclip"):
        command = [
            "xclip",
            "-i",
            "-selection",
            "clipboard",
            "-t",
            "text/uri-list",
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            # same issue here, but i cant even pipe
            # stdout, what in the scuffed code is this
            # who thought this was a great idea
            # # stdout=asyncio.subprocess.PIPE,
            # # stderr=asyncio.subprocess.PIPE,
        )
        stdin = "\n".join([Path(path).resolve().as_uri() for path in paths]).encode()
        using = "xclip"
    else:
        raise ClipboardToolNotFoundError(
            "wl-copy/xclip",
            "Linux",
            "Install 'wl-clipboard' for Wayland or 'xclip' for X11 using your package manager.",
        )
    try:
        stdout, stderr = await asyncio.wait_for(
            # pass in files as stdin
            process.communicate(stdin),
            timeout=5,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        exc.add_note(f"{using} timed out")
        raise exc from None
    return CompletedProcess(
        returncode=process.returncode or 0,
        args=command,
        stdout="" if stdout is None else stdout.decode().strip(),
        stderr="" if stderr is None else stderr.decode().strip(),
    )
