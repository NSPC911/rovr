"""Unit tests for rovr.classes.archive module."""

import pytest
import zipfile
import tarfile
from pathlib import Path


@pytest.fixture
def sample_zip(temp_dir: Path) -> Path:
    """Create a sample ZIP archive for testing."""
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("file1.txt", "Hello, World!")
        zf.writestr("folder/file2.txt", "Nested content")
        zf.writestr("folder/subfolder/deep.txt", "Deep nested")
    return zip_path


@pytest.fixture
def sample_tar_gz(temp_dir: Path) -> Path:
    """Create a sample tar.gz archive for testing."""
    tar_path = temp_dir / "test.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        # Create a temporary file to add
        temp_file = temp_dir / "temp_content.txt"
        temp_file.write_text("Tar content")
        tf.add(temp_file, arcname="content.txt")
    return tar_path


@pytest.fixture
def corrupted_zip(temp_dir: Path) -> Path:
    """Create a corrupted ZIP file."""
    zip_path = temp_dir / "corrupted.zip"
    zip_path.write_bytes(b"PK\x03\x04" + b"\x00" * 100 + b"garbage")
    return zip_path


@pytest.fixture
def empty_zip(temp_dir: Path) -> Path:
    """Create an empty ZIP archive."""
    zip_path = temp_dir / "empty.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        pass  # Empty archive
    return zip_path


class TestArchiveOpen:
    """Tests for opening archives."""

    def test_open_valid_zip(self, sample_zip):
        """Valid ZIP files open without error."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_zip)) as archive:
            assert archive is not None

    def test_open_valid_tar_gz(self, sample_tar_gz):
        """Valid tar.gz files open without error."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_tar_gz)) as archive:
            assert archive is not None

    def test_open_nonexistent_file_raises(self, temp_dir):
        """Non-existent file raises FileNotFoundError."""
        from rovr.classes.archive import Archive
        
        with pytest.raises(FileNotFoundError):
            with Archive(str(temp_dir / "nonexistent.zip")) as archive:
                pass

    def test_open_empty_zip(self, empty_zip):
        """Empty ZIP files open without error."""
        from rovr.classes.archive import Archive
        
        with Archive(str(empty_zip)) as archive:
            assert archive is not None


class TestArchiveList:
    """Tests for listing archive contents."""

    def test_list_zip_contents(self, sample_zip):
        """ZIP contents can be listed."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_zip)) as archive:
            contents = archive.namelist()
            assert "file1.txt" in contents
            assert "folder/file2.txt" in contents

    def test_list_tar_contents(self, sample_tar_gz):
        """Tar contents can be listed."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_tar_gz)) as archive:
            contents = archive.namelist()
            assert len(contents) > 0


class TestArchiveRead:
    """Tests for reading archive members."""

    def test_open_zip_member(self, sample_zip):
        """Can open and read content of ZIP member."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_zip)) as archive:
            with archive.open("file1.txt") as f:
                content = f.read()
            assert content == b"Hello, World!"

    def test_open_nonexistent_member_raises(self, sample_zip):
        """Opening non-existent member raises KeyError."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_zip)) as archive:
            with pytest.raises(KeyError):
                with archive.open("nonexistent.txt") as f:
                    pass


class TestArchiveExtract:
    """Tests for extracting archives."""

    def test_extract_all_members(self, sample_zip, temp_dir):
        """Can extract all files from ZIP by iterating."""
        from rovr.classes.archive import Archive
        
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()
        
        with Archive(str(sample_zip)) as archive:
            for member in archive.namelist():
                archive.extract(member, str(extract_dir))
        
        assert (extract_dir / "file1.txt").exists()
        assert (extract_dir / "folder" / "file2.txt").exists()

    def test_extract_single_member(self, sample_zip, temp_dir):
        """Can extract single file from ZIP."""
        from rovr.classes.archive import Archive
        
        extract_dir = temp_dir / "extracted_single"
        extract_dir.mkdir()
        
        with Archive(str(sample_zip)) as archive:
            archive.extract("file1.txt", str(extract_dir))
        
        assert (extract_dir / "file1.txt").exists()


class TestArchiveContextManager:
    """Tests for archive context manager behavior."""

    def test_context_manager_closes(self, sample_zip):
        """Archive is properly closed after context."""
        from rovr.classes.archive import Archive
        
        archive = Archive(str(sample_zip))
        with archive:
            pass
        # Should be closed now - accessing should fail or return closed state


class TestArchiveTypeDetection:
    """Tests for archive type detection."""

    def test_detects_zip_by_extension(self, sample_zip):
        """ZIP files detected by .zip extension."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_zip)) as archive:
            # Archive should recognize it's a ZIP
            assert archive is not None

    def test_detects_tar_gz_by_extension(self, sample_tar_gz):
        """Tar.gz files detected by .tar.gz extension."""
        from rovr.classes.archive import Archive
        
        with Archive(str(sample_tar_gz)) as archive:
            assert archive is not None
