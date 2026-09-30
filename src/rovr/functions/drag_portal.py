"""Export dragged files through the XDG desktop portal.

Sandboxed drop targets (Flatpak browsers and apps) cannot open ``file://`` URIs
that point at the host filesystem, so a drag which only offers ``text/uri-list``
arrives as a file they cannot read. ``org.freedesktop.portal.FileTransfer``
exists for exactly this case: the source registers the files and hands out a
key, and the portal exports them into the document store for whichever app asks
them for. The target is the one that ends up with a ``/run/user/UID/doc/...``
path, so the source never has to know where the drag is going.

libsystemd's D-Bus client is used through ctypes because ``AddFiles`` passes
file descriptors, which needs both a real connection and a connection we keep
alive ourselves: the portal ties every transfer to the bus name that started
it, so a throwaway CLI call would be a different sender every time.
"""

from __future__ import annotations

import ctypes
import os
import platform
import threading
from collections.abc import Sequence
from contextlib import suppress
from functools import lru_cache

PORTAL_MIME = "application/vnd.portal.filetransfer"
"""MIME type the transfer key is offered under, as expected by portal-aware apps."""

_BUS_NAME = "org.freedesktop.portal.Documents"
_BUS_PATH = "/org/freedesktop/portal/documents"
_BUS_IFACE = "org.freedesktop.portal.FileTransfer"
# The session bus caps the number of fds carried by a single message at 16.
_FD_CHUNK = 16
_O_PATH = getattr(os, "O_PATH", 0o10000000)

_P = ctypes.c_void_p
_PP = ctypes.POINTER(_P)
_CHAR_P = ctypes.c_char_p


class _BusError(ctypes.Structure):
    """Mirror of ``sd_bus_error``, which libsystemd fills in on failure."""

    _fields_ = [
        ("name", ctypes.c_char_p),
        ("message", ctypes.c_char_p),
        ("need_free", ctypes.c_int),
    ]


class _PortalError(RuntimeError):
    """A portal call was refused or could not be completed."""


_FUNCTIONS: tuple[tuple[str, object, list[object]], ...] = (
    ("sd_bus_open_user", ctypes.c_int, [_PP]),
    (
        "sd_bus_message_new_method_call",
        ctypes.c_int,
        [_P, _PP, _CHAR_P, _CHAR_P, _CHAR_P, _CHAR_P],
    ),
    ("sd_bus_message_append_basic", ctypes.c_int, [_P, ctypes.c_char, _P]),
    ("sd_bus_message_open_container", ctypes.c_int, [_P, ctypes.c_char, _CHAR_P]),
    ("sd_bus_message_close_container", ctypes.c_int, [_P]),
    ("sd_bus_message_read", ctypes.c_int, [_P, _CHAR_P, _P]),
    ("sd_bus_message_unref", _P, [_P]),
    (
        "sd_bus_call",
        ctypes.c_int,
        [_P, _P, ctypes.c_uint64, ctypes.POINTER(_BusError), _PP],
    ),
    ("sd_bus_error_free", None, [ctypes.POINTER(_BusError)]),
)


@lru_cache(maxsize=1)
def _library() -> ctypes.CDLL | None:
    """Load the D-Bus client out of libsystemd, if this system has one.

    Returns:
        The library with its prototypes declared, or None when unavailable.
    """
    try:
        library = ctypes.CDLL("libsystemd.so.0")
    except OSError:
        return None

    for name, restype, argtypes in _FUNCTIONS:
        function = getattr(library, name, None)
        if function is None:
            return None
        function.restype = restype
        function.argtypes = argtypes
    return library


_bus: _P | None = None
_lock = threading.Lock()


def _check(code: int, error: _BusError, action: str) -> None:
    """Turn a negative libsystemd return code into a _PortalError.

    Args:
        code: The return code of the call that failed.
        error: The error struct that call filled in.
        action: What was being attempted, for the message.

    Raises:
        _PortalError: If the code signals failure.
    """
    if code >= 0:
        return
    name = (error.name or b"").decode()
    message = (error.message or b"").decode()
    _free_error(error)
    raise _PortalError(f"{action} failed: {name} {message}".strip())


def _free_error(error: _BusError) -> None:
    """Release the strings libsystemd allocated inside an error struct.

    Args:
        error: The struct to clean up.
    """
    library = _library()
    if library is not None:
        library.sd_bus_error_free(ctypes.byref(error))


def _connection(library: ctypes.CDLL) -> _P:
    """Return the process-wide bus connection, opening it on first use.

    Args:
        library: The loaded libsystemd.

    Returns:
        The bus connection, shared by every call and every thread.
    """
    global _bus
    if _bus is not None:
        return _bus
    handle = _P()
    _check(library.sd_bus_open_user(ctypes.byref(handle)), _BusError(), "open user bus")
    _bus = handle
    return handle


def _new_call(library: ctypes.CDLL, member: str) -> _P:
    """Start building a method call to the FileTransfer portal.

    Args:
        library: The loaded libsystemd.
        member: The method to call.

    Returns:
        An empty message to append the arguments to.
    """
    message = _P()
    _check(
        library.sd_bus_message_new_method_call(
            _connection(library),
            ctypes.byref(message),
            _BUS_NAME.encode(),
            _BUS_PATH.encode(),
            _BUS_IFACE.encode(),
            member.encode(),
        ),
        _BusError(),
        member,
    )
    return message


def _invoke(library: ctypes.CDLL, message: _P) -> _P:
    """Send a prepared method call and return its reply.

    Args:
        library: The loaded libsystemd.
        message: The message to send, with all arguments appended.

    Returns:
        The reply message, which the caller owns.
    """
    reply = _P()
    error = _BusError()
    _check(
        library.sd_bus_call(_connection(library), message, 0, ctypes.byref(error), ctypes.byref(reply)),
        error,
        "portal call",
    )
    library.sd_bus_message_unref(message)
    return reply


def _append_string(library: ctypes.CDLL, message: _P, text: str) -> None:
    """Append a string argument to a message.

    Args:
        library: The loaded libsystemd.
        message: The message being built.
        text: The string to append.
    """
    raw = _CHAR_P(text.encode())
    _check(
        library.sd_bus_message_append_basic(message, b"s", ctypes.cast(raw, _P)),
        _BusError(),
        "append string",
    )


def _append_fd(library: ctypes.CDLL, message: _P, descriptor: int) -> None:
    """Append a file descriptor argument to a message.

    Args:
        library: The loaded libsystemd.
        message: The message being built.
        descriptor: The open fd, which libsystemd duplicates.
    """
    as_int = ctypes.c_int(descriptor)
    _check(
        library.sd_bus_message_append_basic(message, b"h", ctypes.byref(as_int)),
        _BusError(),
        "append fd",
    )


def _append_options(library: ctypes.CDLL, message: _P) -> None:
    """Append an empty options vardict to a message.

    Args:
        library: The loaded libsystemd.
        message: The message being built.
    """
    _check(
        library.sd_bus_message_open_container(message, b"a", b"{sv}"),
        _BusError(),
        "open options",
    )
    _check(library.sd_bus_message_close_container(message), _BusError(), "close options")


def _start_transfer(library: ctypes.CDLL) -> str:
    """Open a transfer session.

    Args:
        library: The loaded libsystemd.

    Returns:
        The key a target needs to retrieve the files.

    Raises:
        _PortalError: If the portal answered without a key.
    """
    message = _new_call(library, "StartTransfer")
    _append_options(library, message)
    reply = _invoke(library, message)
    try:
        key = _CHAR_P()
        if library.sd_bus_message_read(reply, b"s", ctypes.byref(key)) <= 0 or not key.value:
            raise _PortalError("StartTransfer returned no key")
        return key.value.decode()
    finally:
        library.sd_bus_message_unref(reply)


def _add_chunk(library: ctypes.CDLL, key: str, descriptors: Sequence[int]) -> None:
    """Register one batch of file descriptors with a session.

    Args:
        library: The loaded libsystemd.
        key: The session to add the files to.
        descriptors: Open fds for the files, at most ``_FD_CHUNK`` of them.
    """
    message = _new_call(library, "AddFiles")
    _append_string(library, message, key)
    _check(library.sd_bus_message_open_container(message, b"a", b"h"), _BusError(), "open fds")
    for descriptor in descriptors:
        _append_fd(library, message, descriptor)
    _check(library.sd_bus_message_close_container(message), _BusError(), "close fds")
    _append_options(library, message)
    library.sd_bus_message_unref(_invoke(library, message))


def _add_files(library: ctypes.CDLL, key: str, paths: Sequence[str]) -> None:
    """Register every dragged path with a session, in batches of open fds.

    Args:
        library: The loaded libsystemd.
        key: The session to add the files to.
        paths: The files and directories about to be dragged.

    Raises:
        OSError: If one of the paths disappeared before it could be opened.
    """
    descriptors: list[int] = []
    try:
        for path in paths:
            descriptors.append(os.open(path, _O_PATH | os.O_CLOEXEC))
        for start in range(0, len(descriptors), _FD_CHUNK):
            _add_chunk(library, key, descriptors[start : start + _FD_CHUNK])
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


def _stop_transfer(library: ctypes.CDLL, key: str) -> None:
    """Close a session.

    Args:
        library: The loaded libsystemd.
        key: The session to close.
    """
    message = _new_call(library, "StopTransfer")
    _append_string(library, message, key)
    library.sd_bus_message_unref(_invoke(library, message))


class DragTransfer:
    """A live portal session backing one drag."""

    def __init__(self, key: str) -> None:
        self._key = key

    @property
    def mime_data(self) -> bytes:
        """The payload to offer under ``PORTAL_MIME``.

        Returns:
            The session key, NUL terminated the way GTK sends it.
        """
        return self._key.encode() + b"\x00"

    def stop(self) -> None:
        """End the session, ignoring failures.

        Only worth calling for drags that never landed: a target that did drop
        may still be fetching the files when the terminal reports the drag as
        finished, and closing the session underneath it makes them unavailable.
        """
        library = _library()
        if library is None:
            return
        with _lock, suppress(_PortalError):
            _stop_transfer(library, self._key)


def export_files(paths: Sequence[str]) -> DragTransfer | None:
    """Register the files of a drag-out with the XDG FileTransfer portal.

    Portal-aware targets pick up the key and ask the portal for the files, which
    hands them paths inside the document store they are allowed to read. Every
    other target keeps using ``text/uri-list`` as before, so this only ever adds
    an option to the drag.

    Args:
        paths: The files and directories about to be dragged.

    Returns:
        The live session, or None when the portal is unavailable or refused the
        files, in which case the drag should go on without it.
    """
    library = _library() if platform.system() == "Linux" else None
    if library is None or not paths:
        return None

    with _lock:
        try:
            key = _start_transfer(library)
        except (OSError, _PortalError):
            return None
        try:
            _add_files(library, key, paths)
        except (OSError, _PortalError):
            with suppress(_PortalError):
                _stop_transfer(library, key)
            return None
    return DragTransfer(key)


__all__ = ["DragTransfer", "PORTAL_MIME", "export_files"]
