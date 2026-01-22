# with reference from https://gitee.com/DreamMaoMao/clipboard.yazi
import asyncio
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    returncode: int
    args: list[str]
    stdout: str
    stderr: str


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
    def __init__(self, tool: str, returncode: int, stderr: str | None = None) -> None:
        self.tool = tool
        self.returncode = returncode
        self.stderr = stderr
        message = f"Clipboard command '{tool}' failed with exit code {returncode}"
        if stderr and stderr.strip():
            message += f": {stderr.strip()}"
        super().__init__(message)


async def copy_files_to_system_clipboard(paths: list[str]) -> bool | ClipboardError:
    """Copy file paths to the system clipboard.

    Args:
        paths: List of file paths to copy.

    Returns:
        True if successful, or a ClipboardError if something went wrong.
    """
    system = platform.system().lower()
    try:
        if system == "windows":
            output = await _copy_windows(paths)
        elif system == "darwin":
            output = await _copy_macos(paths)
        elif system == "linux":
            output = await _copy_linux(paths)
        else:
            return ClipboardError(f"Unsupported platform: {system}")

        if output is None:
            return True  # No operation needed for empty paths
        elif output.returncode == 0:
            return True
        else:
            tool = output.args[0] if output.args else "unknown"
            return ClipboardCommandError(tool, output.returncode, output.stderr)
    except TimeoutError as exc:
        return ClipboardError(f"Clipboard operation timed out: {exc}")
    except ClipboardError as exc:
        return exc
    except Exception as exc:
        return ClipboardError(f"Unexpected error: {exc}")


async def _copy_windows(paths: list[str]) -> ProcessResult | None:
    if not paths:
        return None

    if not shutil.which("powershell"):
        raise ClipboardToolNotFoundError(
            "powershell", "Windows", "PowerShell should be available on Windows"
        )

    escaped_paths = [f"'{path.replace('"', '`"')}'" for path in paths]
    paths_list = ",".join(escaped_paths)

    command = [
        "powershell",
        "-Command",
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"$data = New-Object System.Collections.Specialized.StringCollection; "
        f"$data.AddRange(@({paths_list})); "
        "[System.Windows.Forms.Clipboard]::SetFileDropList($data)",
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    return ProcessResult(
        returncode=process.returncode or 0,
        args=command,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
    )


async def _copy_macos(paths: list[str]) -> ProcessResult | None:
    if not paths:
        return None

    # as much as I want to use osascript, there is no way
    # to add multiple files to it. No, pbcopy does not support files.
    # so we are forced to use https://github.com/neilberkman/clippy
    if not shutil.which("clippy"):
        raise ClipboardToolNotFoundError(
            "clippy",
            "macOS",
            "Install 'clippy' via Homebrew: 'brew install clippy'\nIf you know how to use osascript to copy files, please open an issue!",
        )
    command = ["clippy"] + [f'"{path}"' for path in paths]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    return ProcessResult(
        returncode=process.returncode or 0,
        args=command,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
    )


async def _copy_linux(paths: list[str]) -> ProcessResult | None:
    if not paths:
        return None

    encoded_paths = [f"{Path(path).resolve().as_uri()}\n" for path in paths]

    # Try wl-copy first (Wayland)
    if shutil.which("wl-copy"):
        command = ["wl-copy", "--type", "text/uri-list", "--"] + encoded_paths
        print(command)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            # quite weird, the issue with this is that
            # i must not pipe wl-copy's 2 stream
            # to null, so im forced to leave stderr open
            # stderr=asyncio.subprocess.STDOUT,
        )
    # Fall back to xclip (X11)
    elif shutil.which("xclip"):
        command = [
            "xclip",
            "-i",
            "-selection",
            "clipboard",
            "-t",
            "x-special/gnome-copied-files",
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=("copy\n" + "".join(encoded_paths)).encode()),
                timeout=15,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise NotImplementedError(command)
        return ProcessResult(
            returncode=process.returncode or 0,
            args=command,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
        )
    else:
        raise ClipboardToolNotFoundError(
            "wl-copy or xclip",
            "Linux",
            "Install 'wl-clipboard' (Wayland) or 'xclip' (X11) via your package manager",
        )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise NotImplementedError(command)
    return ProcessResult(
        returncode=process.returncode or 0,
        args=command,
        stdout="" if stdout is None else stdout.decode().strip(),
        stderr="" if stderr is None else stderr.decode().strip(),
    )
