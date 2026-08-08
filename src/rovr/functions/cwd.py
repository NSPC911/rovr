import os
from os import path


def _initial_cwd() -> str:
    """Choose a valid logical cwd when the module is imported.

    The inherited ``PWD`` is retained only when it is absolute and points to
    the process's physical working directory. This preserves a symlink path
    supplied by the launching shell without trusting a stale environment value.

    Returns:
        The validated logical cwd, or the physical cwd as a fallback.
    """
    physical_cwd = os.getcwd()
    pwd = os.environ.get("PWD")
    if pwd is not None and path.isabs(pwd):
        try:
            if path.samefile(pwd, physical_cwd):
                return path.normpath(pwd)
        except OSError:
            pass
    return physical_cwd


_logical_cwd = _initial_cwd()


def getcwd() -> str:
    """Return the logical cwd, preserving traversed directory symlinks.

    The tracked path is checked against the process's physical cwd on every
    call. If another caller changed directories or the logical path disappeared,
    the physical cwd becomes the new logical cwd.

    Returns:
        The logical current working directory.
    """
    global _logical_cwd

    physical_cwd = os.getcwd()
    try:
        if path.samefile(_logical_cwd, physical_cwd):
            return _logical_cwd
    except OSError:
        pass

    _logical_cwd = physical_cwd
    os.environ["PWD"] = physical_cwd
    return physical_cwd


def chdir(directory: str) -> None:
    """Change directory while retaining the logical path used to reach it.

    Args:
        directory: An absolute path or a path relative to the logical cwd.
    """
    global _logical_cwd

    logical_cwd = getcwd()
    logical_directory = (
        path.normpath(directory)
        if path.isabs(directory)
        else path.normpath(path.join(logical_cwd, directory))
    )
    os.chdir(directory)
    _logical_cwd = logical_directory
    os.environ["PWD"] = logical_directory


__all__ = ["getcwd", "chdir"]
