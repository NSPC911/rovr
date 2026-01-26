# this is the only file in the entire repository that is written fully by AI
import bz2 as bzip2
import gzip
import lzma
import sys
import zipfile
from pathlib import Path
from types import TracebackType
from typing import IO, List, Literal, NamedTuple

import rarfile

if sys.version_info <= (3, 13):
    try:
        from backports.zstd import tarfile
    except ModuleNotFoundError:
        import tarfile
else:
    import tarfile


class BadArchiveError(Exception):
    """Custom exception for handling bad or unsupported archive files."""


class ArchiveExtensions(NamedTuple):
    zip: tuple[str, ...]
    rar: tuple[str, ...]
    tar: tuple[str, ...]
    gz: tuple[str, ...]
    bz2: tuple[str, ...]
    xz: tuple[str, ...]
    zst: tuple[str, ...]


ARCHIVE_EXTENSIONS = ArchiveExtensions(
    (".zip",),
    (".rar",),
    (".tar",),
    (".tgz", ".tar.gz"),
    (".tbz", ".tbz2", ".tar.bz2"),
    (".tar.xz", ".tar.lzma"),
    (".tzst", ".tar.zst"),
)


class Archive:
    """Unified handler for ZIP, TAR and RAR files with context manager support."""

    def __init__(
        self,
        filename: str | Path,
        algo: Literal["zip", "tar", "rar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"]
        | None = None,
        mode: str = "r",
        compression_level: int | None = None,
    ) -> None:
        """Initialize the archive handler.

        Args:
            filename: Path to the archive file
            mode: File access mode ('r' for read, 'w' for write, 'a' for append)
            compression_level: Compression level (ZIP: 0-9, TAR gzip: 0-9, TAR bzip2: 1-9)
                             If None, uses default compression

        Raises:
            ValueError: If mode is not supported or compression_level is out of range
        """  # noqa: DOC502
        self.filename = str(filename)
        self.mode = mode
        self.compression_level = compression_level
        self.algo = algo
        self._archive: zipfile.ZipFile | tarfile.TarFile | rarfile.RarFile | None = None
        self._archive_type: Literal["zip", "rar", "tar"] | None = None
        self._compress_file_obj: IO[bytes] | None = None

    def __enter__(self) -> "Archive":
        """Context manager entry - opens the archive.

        Returns:
            Self for method chaining in with statement
        """
        self._detect_and_open()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit - closes the archive.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Traceback if an exception occurred
        """
        if self._archive:
            self._archive.close()
        if self._compress_file_obj:
            self._compress_file_obj.close()

    def _detect_and_open(self) -> None:
        """Detect file type and open appropriate handler.

        For read mode, attempts to open as ZIP, then RAR, then TAR by trying each
        format and catching format-specific errors. For write mode, uses file
        extension to determine the format.

        Raises:
            FileNotFoundError: If the archive file doesn't exist (for read mode)
            ValueError: If file extension is not recognized or compression_level is invalid
            BadArchiveError: If the archive cannot be opened due to format errors
        """
        try:
            if self.mode == "r":
                self._detect_and_open_read()
            else:
                self._detect_and_open_write()
        except (zipfile.BadZipFile, tarfile.TarError, rarfile.BadRarFile) as exc:
            raise BadArchiveError(f"Failed to open archive. {exc}") from exc
        except (FileNotFoundError, ValueError):
            raise

    def _detect_and_open_read(self) -> None:
        """Attempt to open archive for reading by trying each format.

        Tries ZIP first, then RAR, then TAR. Uses actual file content detection
        rather than relying on file extensions.

        Raises:
            FileNotFoundError: If the archive file doesn't exist
            ValueError: If file cannot be opened as any supported archive format,
                       or if the archive is password-protected
        """  # noqa: DOC502
        # Try ZIP first
        try:
            archive = zipfile.ZipFile(self.filename, "r")
            # Check for password protection
            if any(zinfo.flag_bits & 0x1 for zinfo in archive.infolist()):
                archive.close()
                raise ValueError("Password-protected ZIP files are not supported")
            self._archive = archive
            self._archive_type = "zip"
            return
        except zipfile.BadZipFile:
            pass

        # Try RAR
        try:
            archive = rarfile.RarFile(self.filename, "r")
            # Check for password protection
            if archive.needs_password():
                archive.close()
                raise ValueError("Password-protected RAR files are not supported")
            self._archive = archive
            self._archive_type = "rar"
            return
        except rarfile.NotRarFile:
            pass

        # Try TAR (with auto-detection for compression)
        try:
            self._archive = tarfile.open(self.filename, "r:*")  # noqa: SIM115
            self._archive_type = "tar"
            return
        except tarfile.TarError:
            pass

        raise ValueError(
            f"Cannot open '{self.filename}': not a valid ZIP, RAR, or TAR archive"
        )

    def _detect_and_open_write(self) -> None:
        """Open archive for writing based on file extension.

        Raises:
            ValueError: If file extension is not recognized or compression_level is invalid
        """
        filename_lower = self.filename.lower()

        if filename_lower.endswith(ARCHIVE_EXTENSIONS.zip) or (self.algo == "zip"):
            self._archive_type = "zip"
            if self.compression_level is not None:
                if not (0 <= self.compression_level <= 9):
                    raise ValueError("ZIP compression level must be between 0-9")
                self._archive = zipfile.ZipFile(
                    self.filename, self.mode, compresslevel=self.compression_level
                )
            else:
                self._archive = zipfile.ZipFile(self.filename, self.mode)
        elif filename_lower.endswith(ARCHIVE_EXTENSIONS.rar) or (self.algo == "rar"):
            raise ValueError("RAR files can only be opened in read mode ('r')")
        else:
            # Assume it's a tar file
            self._archive_type = "tar"
            tar_mode = self._get_tar_write_mode()
            if self.compression_level is not None:
                self._archive = self._open_tar_with_compression(tar_mode)
            else:
                self._archive = tarfile.open(self.filename, tar_mode)  # noqa: SIM115

    def _get_tar_write_mode(self) -> Literal["w:gz", "w:bz2", "w:xz", "w:zst", "w"]:
        """Determine tar write mode based on file extension.

        Returns:
            Appropriate tarfile mode string for writing
        """
        filename_lower = self.filename.lower()
        if filename_lower.endswith(ARCHIVE_EXTENSIONS.gz) or (self.algo == "tar.gz"):
            return "w:gz"
        elif filename_lower.endswith(ARCHIVE_EXTENSIONS.bz2) or (
            self.algo == "tar.bz2"
        ):
            return "w:bz2"
        elif filename_lower.endswith(ARCHIVE_EXTENSIONS.xz) or (self.algo == "tar.xz"):
            return "w:xz"
        elif filename_lower.endswith(ARCHIVE_EXTENSIONS.zst) or (
            self.algo == "tar.zst"
        ):
            return "w:zst"
        else:
            return "w"

    def _open_tar_with_compression(
        self, tar_mode: Literal["w:gz", "w:bz2", "w:xz", "w:zst", "w"]
    ) -> tarfile.TarFile:
        """Open TAR file with specified compression level.

        Args:
            tar_mode: TAR mode string (e.g., 'w:gz', 'w:bz2')

        Returns:
            Opened TarFile with compression level applied

        Raises:
            ValueError: If compression level is invalid for the compression type
        """
        assert self.compression_level is not None

        if ":gz" in tar_mode:
            if not (0 <= self.compression_level <= 9):
                raise ValueError("Gzip compression level must be between 0-9")
            self._compress_file_obj = gzip.open(  # noqa: SIM115
                self.filename, self.mode + "b", compresslevel=self.compression_level
            )
            return tarfile.open(fileobj=self._compress_file_obj, mode="w")

        elif ":bz2" in tar_mode:
            if not (1 <= self.compression_level <= 9):
                raise ValueError("Bzip2 compression level must be between 1-9")
            self._compress_file_obj = bzip2.open(  # noqa: SIM115
                self.filename, self.mode + "b", compresslevel=self.compression_level
            )
            return tarfile.open(fileobj=self._compress_file_obj, mode="w")

        elif ":xz" in tar_mode:
            if not (0 <= self.compression_level <= 9):
                raise ValueError("XZ compression level must be between 0-9")
            xz_file = lzma.open(  # noqa: SIM115
                self.filename, self.mode + "b", preset=self.compression_level
            )
            return tarfile.open(fileobj=xz_file, mode="w")
        elif ":zst" in tar_mode:
            if not (1 <= self.compression_level <= 22):
                raise ValueError("Zstandard compression level must be between 1-22")
            return tarfile.open(self.filename, tar_mode, level=self.compression_level)
        else:
            return tarfile.open(self.filename, compresslevel=self.compression_level)

    def infolist(
        self,
    ) -> list[zipfile.ZipInfo] | list[tarfile.TarInfo] | list[rarfile.RarInfo]:
        """Return list of archive members (similar to zipfile.infolist()).

        Returns:
            List of ZipInfo, TarInfo or RarInfo objects

        Raises:
            RuntimeError: If archive is not opened
            BadArchiveError: If the archive cannot be listed due to any archive related errors
            FileNotFoundError: If the file is no longer available
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        try:
            match self._archive_type:
                case "rar":
                    assert isinstance(self._archive, rarfile.RarFile)
                    return self._archive.infolist()
                case "zip":
                    assert isinstance(self._archive, zipfile.ZipFile)
                    return self._archive.infolist()
                case _:
                    assert isinstance(self._archive, tarfile.TarFile)
                    return self._archive.getmembers()
        except (zipfile.BadZipFile, tarfile.TarError, rarfile.BadRarFile) as exc:
            raise BadArchiveError(f"Failed to open archive. {exc}") from exc
        except FileNotFoundError:
            raise

    def namelist(self) -> List[str]:
        """Return list of member names.

        Returns:
            List of strings containing all member file/directory names in the archive

        Raises:
            RuntimeError: If archive is not opened
            BadArchiveError: If the archive cannot be listed due to any archive related errors
            FileNotFoundError: If the file is no longer available
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        try:
            match self._archive_type:
                case "zip":
                    assert isinstance(self._archive, zipfile.ZipFile)
                    return self._archive.namelist()
                case "rar":
                    assert isinstance(self._archive, rarfile.RarFile)
                    return self._archive.namelist()
                case _:
                    assert isinstance(self._archive, tarfile.TarFile)
                    return self._archive.getnames()
        except (zipfile.BadZipFile, tarfile.TarError, rarfile.BadRarFile) as exc:
            raise BadArchiveError(f"Failed to open archive. {exc}") from exc
        except FileNotFoundError:
            raise

    def extract(
        self,
        member: str | zipfile.ZipInfo | tarfile.TarInfo | rarfile.RarInfo,
        path: str | Path = "",
    ) -> str:
        """Extract a single member to the specified path.

        Args:
            member: Name of the file to extract, or ZipInfo/TarInfo/RarInfo object
            path: Directory to extract to. If None, extracts to current directory

        Returns:
            Path to the extracted file

        Raises:
            RuntimeError: If archive is not opened
            BadArchiveError: If the extraction fails due to archive related errors
            FileNotFoundError: If the file is no longer available
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        try:
            match self._archive_type:
                case "rar":
                    assert isinstance(self._archive, rarfile.RarFile)
                    member_filename = (
                        member.filename
                        if isinstance(member, rarfile.RarInfo)
                        else member
                    )
                    self._archive.extract(member, path)
                    return str(Path(path or ".") / member_filename)
                case "zip":
                    assert isinstance(self._archive, zipfile.ZipFile)
                    member_arg = (
                        member
                        if isinstance(member, (str, zipfile.ZipInfo))
                        else str(member)
                    )
                    return self._archive.extract(member_arg, path)
                case _:
                    assert isinstance(self._archive, tarfile.TarFile)
                    member_arg = (
                        member
                        if isinstance(member, (str, tarfile.TarInfo))
                        else str(member)
                    )
                    result = self._archive.extract(member_arg, path)
                    return (
                        str(result)
                        if result
                        else str(Path(path or ".") / str(member_arg))
                    )
        except (zipfile.BadZipFile, tarfile.TarError, rarfile.BadRarFile) as exc:
            raise BadArchiveError(f"Failed to extract member. {exc}") from exc
        except FileNotFoundError:
            raise

    def open(
        self,
        member: str | zipfile.ZipInfo | tarfile.TarInfo | rarfile.RarInfo,
        mode: Literal["r", "w"] = "r",
    ) -> IO[bytes] | None:
        """Open a member file for reading.

        Args:
            member: Name of the file to open, or ZipInfo/TarInfo/RarInfo object
            mode: File open mode (only 'r' supported for TAR and RAR files)

        Returns:
            File-like object for reading the member's contents, or None if member
            is a directory or cannot be opened

        Raises:
            RuntimeError: If archive is not opened
            ValueError: If a RAR file is attempted to be opened in anything that isn't read mode
            BadArchiveError: If the member cannot be opened due to archive related errors
            FileNotFoundError: If the file is no longer available
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        try:
            match self._archive_type:
                case "zip":
                    assert isinstance(self._archive, zipfile.ZipFile)
                    member_arg = (
                        member
                        if isinstance(member, (str, zipfile.ZipInfo))
                        else str(member)
                    )
                    return self._archive.open(member_arg, mode)
                case "rar":
                    assert isinstance(self._archive, rarfile.RarFile)
                    if mode != "r":
                        raise ValueError(
                            "RAR members can only be opened in read mode ('r')"
                        )
                    member_arg = (
                        member
                        if isinstance(member, (str, rarfile.RarInfo))
                        else str(member)
                    )
                    return self._archive.open(member_arg, mode)
                case _:
                    assert isinstance(self._archive, tarfile.TarFile)
                    member_arg = (
                        member
                        if isinstance(member, (str, tarfile.TarInfo))
                        else str(member)
                    )
                    return self._archive.extractfile(member_arg)
        except (zipfile.BadZipFile, tarfile.TarError, rarfile.BadRarFile) as exc:
            raise BadArchiveError(f"Failed to open member. {exc}") from exc
        except FileNotFoundError:
            raise
