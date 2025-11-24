# this is the only file in the entire repository that is written fully by AI
import bz2
import gzip
import lzma
import tarfile
import zipfile
from pathlib import Path
from types import TracebackType
from typing import IO, List, Literal, Optional, Union

import rarfile

from rovr.variables.maps import ARCHIVE_EXTENSIONS


class Archive:
    """Unified handler for ZIP, TAR and RAR files with context manager support."""

    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = "r",
        compression_level: Optional[int] = None,
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
        self._archive: Optional[
            Union[zipfile.ZipFile, tarfile.TarFile, rarfile.RarFile]
        ] = None
        self._is_zip: Optional[bool] = None
        self._is_rar: Optional[bool] = None

    def __enter__(self) -> "Archive":
        """Context manager entry - opens the archive.

        Returns:
            Self for method chaining in with statement

        Raises:
            FileNotFoundError: If the archive file doesn't exist (for read mode)
            zipfile.BadZipFile: If ZIP file is corrupted
            tarfile.TarError: If TAR file is corrupted or unreadable
            rarfile.BadRarFile: If RAR file is corrupted
        """  # noqa: DOC502
        self._detect_and_open()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit - closes the archive.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Traceback if an exception occurred
        """
        """Context manager exit - closes the archive."""
        if self._archive:
            self._archive.close()

    def _detect_and_open(self) -> None:
        """Detect file type and open appropriate handler.

        Raises:
            FileNotFoundError: If the archive file doesn't exist (for read mode)
            zipfile.BadZipFile: If ZIP file is corrupted
            tarfile.TarError: If TAR file is corrupted or format not supported
            rarfile.BadRarFile: If RAR file is corrupted
            ValueError: If file extension is not recognized or compression_level is invalid
        """  # noqa: DOC502
        filename_lower = self.filename.lower()

        if filename_lower.endswith(ARCHIVE_EXTENSIONS.zip):
            self._is_zip = True
            self._is_rar = False
            if self.compression_level is not None:
                if not (0 <= self.compression_level <= 9):
                    raise ValueError("ZIP compression level must be between 0-9")
                self._archive = zipfile.ZipFile(
                    self.filename, self.mode, compresslevel=self.compression_level
                )
            else:
                self._archive = zipfile.ZipFile(self.filename, self.mode)
            # Check for password protection
            if self.mode == "r":
                assert isinstance(self._archive, zipfile.ZipFile)
                if any(zinfo.flag_bits & 0x1 for zinfo in self._archive.infolist()):
                    self._archive.close()
                    raise ValueError("Password-protected ZIP files are not supported")
        elif filename_lower.endswith(ARCHIVE_EXTENSIONS.rar):
            self._is_zip = False
            self._is_rar = True
            if self.mode != "r":
                raise ValueError("RAR files can only be opened in read mode ('r')")
            self._archive = rarfile.RarFile(self.filename, self.mode)
            # Check for password protection
            assert isinstance(self._archive, rarfile.RarFile)
            if self._archive.needs_password():
                self._archive.close()
                raise ValueError("Password-protected RAR files are not supported")
        else:
            # Assume it's a tar file - let tarfile auto-detect compression
            self._is_zip = False
            self._is_rar = False
            if self.mode == "r":
                self._archive = tarfile.open(self.filename, "r:*")  # noqa: SIM115
            else:
                tar_mode = self._get_tar_write_mode()
                if self.compression_level is not None:
                    self._archive = self._open_tar_with_compression(tar_mode)
                else:
                    self._archive = tarfile.open(self.filename, tar_mode)  # noqa: SIM115

    def _get_tar_write_mode(self) -> Literal["w:gz", "w:bz2", "w:xz", "w"]:
        """Determine tar write mode based on file extension.

        Returns:
            Appropriate tarfile mode string for writing
        """
        filename_lower = self.filename.lower()
        if filename_lower.endswith((".tar.gz", ".tgz")):
            return "w:gz"
        elif filename_lower.endswith((".tar.bz2", ".tbz2")):
            return "w:bz2"
        elif filename_lower.endswith(".tar.xz"):
            return "w:xz"
        else:
            return "w"

    def _open_tar_with_compression(
        self, tar_mode: Literal["w:gz", "w:bz2", "w:xz", "w"]
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
            gz_file = gzip.open(  # noqa: SIM115
                self.filename, self.mode + "b", compresslevel=self.compression_level
            )
            return tarfile.open(fileobj=gz_file, mode="w")

        elif ":bz2" in tar_mode:
            if not (1 <= self.compression_level <= 9):
                raise ValueError("Bzip2 compression level must be between 1-9")
            bz2_file = bz2.open(  # noqa: SIM115
                self.filename, self.mode + "b", compresslevel=self.compression_level
            )
            return tarfile.open(fileobj=bz2_file, mode="w")

        elif ":xz" in tar_mode:
            if not (0 <= self.compression_level <= 9):
                raise ValueError("XZ compression level must be between 0-9")
            xz_file = lzma.open(  # noqa: SIM115
                self.filename, self.mode + "b", preset=self.compression_level
            )
            return tarfile.open(fileobj=xz_file, mode="w")

        else:
            return tarfile.open(self.filename, tar_mode)

    def infolist(
        self,
    ) -> list[zipfile.ZipInfo] | list[tarfile.TarInfo] | list[rarfile.RarInfo]:
        """Return list of archive members (similar to zipfile.infolist()).

        Returns:
            List of ZipInfo, TarInfo or RarInfo objects

        Raises:
            RuntimeError: If archive is not opened
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        if self._is_zip:
            assert isinstance(self._archive, zipfile.ZipFile)
            return self._archive.infolist()
        elif self._is_rar:
            assert isinstance(self._archive, rarfile.RarFile)
            return self._archive.infolist()
        else:
            assert isinstance(self._archive, tarfile.TarFile)
            return self._archive.getmembers()

    def namelist(self) -> List[str]:
        """Return list of member names.

        Returns:
            List of strings containing all member file/directory names in the archive

        Raises:
            RuntimeError: If archive is not opened
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        if self._is_zip:
            assert isinstance(self._archive, zipfile.ZipFile)
            return self._archive.namelist()
        elif self._is_rar:
            assert isinstance(self._archive, rarfile.RarFile)
            return self._archive.namelist()
        else:
            assert isinstance(self._archive, tarfile.TarFile)
            return self._archive.getnames()

    def extract(
        self,
        member: Union[str, zipfile.ZipInfo, tarfile.TarInfo, rarfile.RarInfo],
        path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Extract a single member to the specified path.

        Args:
            member: Name of the file to extract, or ZipInfo/TarInfo/RarInfo object
            path: Directory to extract to. If None, extracts to current directory

        Returns:
            Path to the extracted file

        Raises:
            RuntimeError: If archive is not opened
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        if self._is_rar:
            assert isinstance(self._archive, rarfile.RarFile)
            member_filename = (
                member.filename if isinstance(member, rarfile.RarInfo) else member
            )
            self._archive.extract(member, path)
            return str(Path(path or ".") / member_filename)

        if self._is_zip:
            assert isinstance(self._archive, zipfile.ZipFile)
            member_arg = (
                member if isinstance(member, (str, zipfile.ZipInfo)) else str(member)
            )
            return self._archive.extract(member_arg, path)

        assert isinstance(self._archive, tarfile.TarFile)
        member_arg = (
            member if isinstance(member, (str, tarfile.TarInfo)) else str(member)
        )
        result = self._archive.extract(member_arg, path)
        return str(result) if result else str(Path(path or ".") / str(member_arg))

    def open(
        self,
        member: Union[str, zipfile.ZipInfo, tarfile.TarInfo, rarfile.RarInfo],
        mode: str = "r",
    ) -> Optional[IO[bytes]]:
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
        """
        if not self._archive:
            raise RuntimeError("Archive not opened")

        if self._is_zip:
            assert isinstance(self._archive, zipfile.ZipFile)
            member_arg = (
                member if isinstance(member, (str, zipfile.ZipInfo)) else str(member)
            )
            return self._archive.open(member_arg, mode)
        elif self._is_rar:
            assert isinstance(self._archive, rarfile.RarFile)
            if mode != "r":
                raise ValueError("RAR members can only be opened in read mode ('r')")
            member_arg = (
                member if isinstance(member, (str, rarfile.RarInfo)) else str(member)
            )
            return self._archive.open(member_arg, mode)
        else:
            assert isinstance(self._archive, tarfile.TarFile)
            member_arg = (
                member if isinstance(member, (str, tarfile.TarInfo)) else str(member)
            )
            return self._archive.extractfile(member_arg)
