# with reference from https://gitee.com/DreamMaoMao/clipboard.yazi aside from macos
# macos uses ctypes (yipee) (without pyobjc bridge) or any external dependencies
# like clippy: https://github.com/neilberkman/clippy
import asyncio
import ctypes
import ctypes.util
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    return_code: int
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
) -> bool | ClipboardError | TimeoutError:
    """Copy file paths to the system clipboard.

    Args:
        paths: List of file paths to copy.

    Returns:
        True if successful, or a ClipboardError if something went wrong.
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

        if output is None:
            return True  # No operation needed for empty output
        elif output.return_code == 0:
            return True
        else:
            tool = output.args[0] if output.args else "unknown"
            return ClipboardCommandError(tool, output.return_code, output.stderr)
    except ClipboardError as exc:
        return exc
    except TimeoutError as exc:
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

    escaped_paths = [
        f"'{path.replace('`', '``').replace('"', '`"').replace("'", "`'")}'"
        for path in paths
    ]
    paths_list = ",".join(escaped_paths)

    command = [
        "powershell",
        "-NoProfile",
        "-NoLogo",
        "-NonInteractive",
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
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        exc.add_note("powershell clipboard command timed out")
        raise exc from None
    return ProcessResult(
        return_code=process.returncode or 0,
        args=command,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
    )


async def _copy_macos(paths: list[str]) -> ProcessResult | None:
    if not paths:
        return None

    try:
        _copy_macos_ctypes(paths)
    except ClipboardError:
        raise
    except OSError as exc:
        raise ClipboardError(f"Failed to load macOS frameworks: {exc}")
    except Exception as exc:
        raise ClipboardError(f"macOS clipboard error: \\[{type(exc).__name__}]\n{exc}")
    return ProcessResult(
        return_code=0, args=["ctypes:NSPasteboard"], stdout="", stderr=""
    )


# no, pbcopy is not enough, here is death by ctypes
def _copy_macos_ctypes(paths: list[str]) -> None:
    """Copy file paths to macOS clipboard via ctypes and the Objective-C runtime.

    Raises:
        ClipboardError: If the pasteboard write operation fails.
    """
    objc = ctypes.util.find_library("objc")
    if objc is None:
        raise ClipboardError("Could not find libobjc on this system")
    libobjc = ctypes.cdll.LoadLibrary(objc)
    ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
    objc_getClass = libobjc.objc_getClass
    objc_getClass.restype = ctypes.c_void_p
    objc_getClass.argtypes = [ctypes.c_char_p]

    sel_registerName = libobjc.sel_registerName
    sel_registerName.restype = ctypes.c_void_p
    sel_registerName.argtypes = [ctypes.c_char_p]

    # Typed objc_msgSend wrappers via CFUNCTYPE
    _ptr = ctypes.cast(libobjc.objc_msgSend, ctypes.c_void_p).value
    VP = ctypes.c_void_p
    # id fn(id, SEL)
    msg0 = ctypes.CFUNCTYPE(VP, VP, VP)(_ptr)
    # id fn(id, SEL, id)
    msg1 = ctypes.CFUNCTYPE(VP, VP, VP, VP)(_ptr)
    # id fn(id, SEL, char*)
    msg_s = ctypes.CFUNCTYPE(VP, VP, VP, ctypes.c_char_p)(_ptr)
    # BOOL fn(id, SEL, id)
    msg_b1 = ctypes.CFUNCTYPE(ctypes.c_bool, VP, VP, VP)(_ptr)
    # id fn(id, SEL, NSUInteger)
    msg_i = ctypes.CFUNCTYPE(VP, VP, VP, ctypes.c_ulong)(_ptr)

    def sel(name: str) -> ctypes.c_void_p:
        return sel_registerName(name.encode())

    NSAutoreleasePool = objc_getClass(b"NSAutoreleasePool")
    NSPasteboard = objc_getClass(b"NSPasteboard")
    NSString = objc_getClass(b"NSString")
    NSURL = objc_getClass(b"NSURL")
    NSMutableArray = objc_getClass(b"NSMutableArray")
    NSApplication = objc_getClass(b"NSApplication")

    for name, cls in {
        "NSAutoreleasePool": NSAutoreleasePool,
        "NSPasteboard": NSPasteboard,
        "NSString": NSString,
        "NSURL": NSURL,
        "NSMutableArray": NSMutableArray,
        "NSApplication": NSApplication,
    }.items():
        if not cls:
            raise ClipboardError(f"Failed to load Objective-C class: {name}")

    # init appkit content for clipboard stuff
    msg0(NSApplication, sel("sharedApplication"))

    pool = msg0(msg0(NSAutoreleasePool, sel("alloc")), sel("init"))
    try:
        pasteboard = msg0(NSPasteboard, sel("generalPasteboard"))
        msg0(pasteboard, sel("clearContents"))

        array = msg_i(NSMutableArray, sel("arrayWithCapacity:"), len(paths))
        if not array:
            raise ClipboardError("Failed to create NSMutableArray for clipboard")
        failed_paths: list[str] = []
        for path in paths:
            resolved = str(Path(path).resolve())
            ns_string = msg_s(NSString, sel("stringWithUTF8String:"), resolved.encode())
            if not ns_string:
                failed_paths.append(path)
                continue
            file_url = msg1(NSURL, sel("fileURLWithPath:"), ns_string)
            if not file_url:
                failed_paths.append(path)
                continue
            msg1(array, sel("addObject:"), file_url)

        if failed_paths:
            raise ClipboardError(
                "Failed to create NSURLs for the following paths:\n"
                + "\n".join(failed_paths)
            )
        success = msg_b1(pasteboard, sel("writeObjects:"), array)
        if not success:
            raise ClipboardError("NSPasteboard writeObjects: returned NO")
    finally:
        msg0(pool, sel("drain"))


async def _copy_linux(paths: list[str]) -> ProcessResult | None:
    if not paths:
        return None

    # Try wl-copy first (Wayland)
    if shutil.which("wl-copy"):
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
    elif shutil.which("xclip"):
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
    return ProcessResult(
        return_code=process.return_code or 0,
        args=command,
        stdout="" if stdout is None else stdout.decode().strip(),
        stderr="" if stderr is None else stderr.decode().strip(),
    )
