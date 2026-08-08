import os
from os import path
from threading import RLock


class _WorkingDirectory:
    """Synchronize Rovr's logical cwd with the process cwd."""

    def __init__(self) -> None:
        """Initialize the context from the process cwd and inherited ``PWD``."""
        self._lock = RLock()
        self._physical_cwd = os.getcwd()
        self._logical_cwd = self._initial_cwd()

    def _initial_cwd(self) -> str:
        """Choose a valid logical cwd from the inherited ``PWD``.

        Returns:
            The validated logical cwd, or the physical cwd as a fallback.
        """
        pwd = os.environ.get("PWD")
        if pwd is None or not path.isabs(pwd):
            return self._physical_cwd
        try:
            if path.samefile(pwd, self._physical_cwd):
                return path.normpath(pwd)
        except OSError:
            pass
        return self._physical_cwd

    def getcwd(self) -> str:
        """Return the logical cwd, resynchronizing after external changes.

        Returns:
            The logical current working directory.
        """
        with self._lock:
            physical_cwd = os.getcwd()
            if physical_cwd == self._physical_cwd:
                return self._logical_cwd

            self._physical_cwd = physical_cwd
            self._logical_cwd = physical_cwd
            os.environ["PWD"] = physical_cwd
            return physical_cwd

    def chdir(self, directory: str) -> None:
        """Change directory while retaining the logical path used to reach it.

        Args:
            directory: An absolute path or a path relative to the logical cwd.
        """
        with self._lock:
            logical_directory = (
                path.normpath(directory)
                if path.isabs(directory)
                else path.normpath(path.join(self.getcwd(), directory))
            )
            os.chdir(directory)
            self._physical_cwd = os.getcwd()
            self._logical_cwd = logical_directory
            os.environ["PWD"] = logical_directory


_working_directory = _WorkingDirectory()


def getcwd() -> str:
    """Return the logical current working directory.

    Returns:
        The logical current working directory.
    """
    return _working_directory.getcwd()


def chdir(directory: str) -> None:
    """Change the process and logical working directories.

    Args:
        directory: An absolute path or a path relative to the logical cwd.
    """
    _working_directory.chdir(directory)


__all__ = ["getcwd", "chdir"]
