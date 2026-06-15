import multiprocessing
import multiprocessing.connection
import stat
import subprocess
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from functools import lru_cache
from os import path
from os import stat as os_stat
from typing import Literal, NamedTuple, TypeAlias

from PIL import Image
from PIL.Image import Image as PILImage

from rovr.functions.preview_workers import (
    _depalette,
    resample_bytes_worker,
    resample_file_worker,
    resample_worker,
    svg_image_worker,
)
from rovr.functions.utils import recache, should_cancel
from rovr.variables.constants import RESAMPLING_METHOD, config, file_one

MAX_IMAGE_SIZE: tuple[int, int] = tuple(config["interface"]["image_viewer"]["max_size"])  # ty: ignore
MAX_FONT_SIZE: tuple[int, int] = tuple(config["interface"]["font_preview"]["max_size"])  # ty: ignore


if hasattr(multiprocessing.connection, "PipeConnection"):
    Connection: TypeAlias = (
        multiprocessing.connection.Connection  # ty: ignore
        | multiprocessing.connection.PipeConnection  # ty: ignore
    )
else:
    Connection: TypeAlias = multiprocessing.connection.Connection  # ty: ignore


def _await_resample_process(
    proc: multiprocessing.Process,
    parent_conn: Connection,
) -> tuple[bytes, str, tuple[int, int]] | None:
    """Wait for a resample subprocess, checking for worker cancellation.

    Returns:
        Raw image data tuple, or None if cancelled/failed.
    """
    try:
        while proc.is_alive():
            if should_cancel():
                proc.kill()
                proc.join()
                return None
            if parent_conn.poll(0.2):
                result = parent_conn.recv()
                proc.join()
                if isinstance(result, Exception):
                    raise result
                return result
        proc.join()
        if parent_conn.poll(0):
            result = parent_conn.recv()
            if isinstance(result, Exception):
                raise result
            return result
        return None
    except (EOFError, BrokenPipeError, ConnectionResetError):
        if proc.is_alive():
            proc.kill()
        proc.join()
        return None
    finally:
        parent_conn.close()
        if proc.is_alive():
            proc.kill()
            proc.join()


def _get_resample_pool_size(batch_size: int) -> int:
    cpu_count = multiprocessing.cpu_count()
    poppler_threads = int(config["plugins"]["poppler"]["threads"])
    if poppler_threads <= 0:
        poppler_threads = cpu_count
    return max(1, min(batch_size, poppler_threads, cpu_count))


def _await_resample_futures(
    executor: ProcessPoolExecutor,
    futures: dict[Future[tuple[bytes, str, tuple[int, int]]], int],
) -> list[tuple[bytes, str, tuple[int, int]]]:
    pending: set[Future[tuple[bytes, str, tuple[int, int]]]] = set(futures)
    ordered_results: list[None | tuple[bytes, str, tuple[int, int]]] = [None] * len(
        futures
    )

    try:
        while pending:
            if should_cancel():
                raise RuntimeError("PDF page resampling was cancelled.")
            done, pending = wait(
                pending,
                timeout=0.2,
                return_when=FIRST_COMPLETED,
            )
            for future in done:
                ordered_results[futures[future]] = future.result()
    except Exception:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise

    executor.shutdown(wait=True)
    results: list[tuple[bytes, str, tuple[int, int]]] = []
    for result in ordered_results:
        if result is None:
            raise RuntimeError("Failed to collect all PDF resample results.")
        results.append(result)
    return results


def resample_batch(images: list[PILImage]) -> list[PILImage]:
    if len(images) == 0:
        return []
    if should_cancel():
        raise RuntimeError("PDF page resampling was cancelled.")

    payloads = []
    for image in images:
        image = _depalette(image)
        payloads.append((
            image.tobytes(),
            image.mode,
            image.size,
            MAX_IMAGE_SIZE,
            RESAMPLING_METHOD(),
        ))
    executor = ProcessPoolExecutor(max_workers=_get_resample_pool_size(len(payloads)))
    try:
        futures = {
            executor.submit(resample_worker, payload): index
            for index, payload in enumerate(payloads)
        }
    except Exception:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    results = _await_resample_futures(executor, futures)
    return [Image.frombytes(mode, size, data) for data, mode, size in results]


def resample(image: Image.Image) -> Image.Image:
    """Resample an in-memory image in a subprocess that can be killed.

    Returns:
        The resampled image, or the original if cancelled.
    """
    image = _depalette(image)
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=resample_bytes_worker,
        args=(
            child_conn,
            image.tobytes(),
            image.mode,
            image.size,
            MAX_IMAGE_SIZE,
            RESAMPLING_METHOD(),
        ),
    )
    proc.start()
    child_conn.close()

    result = _await_resample_process(proc, parent_conn)
    if result is None:
        return image
    data, mode, size = result
    return Image.frombytes(mode, size, data)


def resample_file(file_path: str) -> Image.Image | None:
    """Open and resample an image file in a Process.

    Returns:
        The resampled image, or None if the worker was cancelled.

    Raises:
        Same exceptions as Image.open (UnidentifiedImageError, etc.).
    """
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=resample_file_worker,
        args=(child_conn, file_path, MAX_IMAGE_SIZE, RESAMPLING_METHOD()),
    )
    proc.start()
    child_conn.close()

    result = _await_resample_process(proc, parent_conn)
    if result is None:
        return None
    data, mode, size = result
    return Image.frombytes(mode, size, data)


def load_svg(file_path: str) -> bytes | None:
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=svg_image_worker, args=(child_conn, file_path)
    )
    proc.start()
    child_conn.close()

    # wait for it to complete
    while proc.is_alive():
        if should_cancel():
            proc.kill()
            proc.join()
            return b"cancelled"
        if parent_conn.poll(0.2):
            result = parent_conn.recv()
            proc.join()
            if isinstance(result, Exception):
                if proc.is_alive():
                    proc.kill()
                proc.join()
            return result
    proc.join()
    if parent_conn.poll(0):
        result = parent_conn.recv()
        if isinstance(result, Exception):
            raise result
        return result
    return None


def load_svg_sync(file_path: str) -> bytes | None:
    from resvg_py import svg_to_bytes

    return svg_to_bytes(svg_path=file_path)


def resample_file_sync(file_path: str) -> Image.Image | None:
    image = Image.open(file_path)
    image = _depalette(image)
    return image.resize(MAX_IMAGE_SIZE, RESAMPLING_METHOD())


def resample_sync(image: Image.Image) -> Image.Image:
    image = _depalette(image)
    return image.resize(MAX_IMAGE_SIZE, RESAMPLING_METHOD())


def resample_batch_sync(images: list[PILImage]) -> list[PILImage]:
    return [
        _depalette(image).resize(MAX_IMAGE_SIZE, RESAMPLING_METHOD())
        for image in images
    ]


# surely the user doesn't go through 256 unique mime types right?
@lru_cache(maxsize=256)
def match_mime_to_preview_type(
    mime_type: str,
) -> (
    Literal["text", "image", "pdf", "archive", "folder", "remime", "resvg", "font"]
    | None
):
    """Match a MIME type against configured rules to determine preview type.

    Args:
        mime_type: The MIME type to match (e.g., "text/plain", "image/png")

    Returns:
        str : The preview type ("text", "image", "pdf", "archive", "folder")
        None: None if no rule matches
    """
    for pattern, preview_type in config["settings"]["preview_rules"].items():
        if recache(pattern).fullmatch(mime_type):
            return preview_type
    return None


class MimeResult(NamedTuple):
    method: Literal["basic", "puremagic", "file1"]
    mime_type: str


@lru_cache(maxsize=8192)
def get_mime_type(
    file_path: str,
    mtime: int | float,
    ignore: tuple[Literal["basic", "puremagic", "file1"], ...] | None = None,
) -> MimeResult | None:
    """
    Synchronous/Threaded wrapper to get the MIME type of a file.

    Args:
        file_path: Path to the file to check
        mtime: The last modified time of the file, used for caching purposes
        ignore: List of detection methods to skip

    Returns:
        MimeResult: The method used and the detected MIME type
        None: If the method is not available or failed

    Raises:
        FileNotFoundError: If file(1) executable is unavailable when that method is selected.
        ╰╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┴> Ruff wants this part here, even though the function
                           handles it internally, so I'm just leaving it here
    """
    if ignore is None:
        ignore = ()

    base = path.basename(file_path)
    if base.startswith("."):
        file_extension = base[1:]
    else:
        file_extension = "".join(base.split(".")[1:]).lower()

    # CHECK IF IT IS A SOCKET OR FIFO
    if stat.S_ISFIFO(mode := os_stat(file_path).st_mode):
        return MimeResult("basic", "inode/fifo")
    elif stat.S_ISSOCK(mode):
        return MimeResult("basic", "inode/socket")

    # Read file bytes once, reuse for both puremagic and basic detection
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read(1024)  # Read first 1KiB
    except OSError:
        # Cannot open file at all
        return None

    # Step 1: Try puremagic (magic byte detection) first
    if "puremagic" not in ignore:
        import puremagic

        try:
            puremagic_result: list[puremagic.PureMagicWithConfidence] = (
                puremagic.magic_string(file_bytes)
            )
            if puremagic_result:
                # If multiple matches exist, prefer one matching the file extension
                for match in puremagic_result:
                    if match.extension.lower() == file_extension and match.mime_type:
                        return MimeResult("puremagic", match.mime_type)
                # Otherwise, return first result with a mime type
                for match in puremagic_result:
                    if match.mime_type:
                        return MimeResult("puremagic", match.mime_type)
        except Exception:
            # puremagic failed, continue to next method
            pass

    # Step 2: Try decoding as text, checking all encodings in order of most likely
    # If puremagic didn't recognise it, it might perhaps be a plain text file
    if "basic" not in ignore:
        from textual.highlight import guess_language

        encodings_to_try = [
            "utf8",
            "utf16",
            "utf32",
            "latin1",
            "iso8859-1",
            "mbcs",
            "ascii",
            "us-ascii",
        ]

        for encoding in encodings_to_try:
            try:
                content = file_bytes.decode(encoding)
                return MimeResult("basic", f"text/{guess_language(content, file_path)}")
            except UnicodeDecodeError:
                pass

    # Step 3: Fall back to file(1) command if available
    if "file1" not in ignore:
        try:
            file_executable = file_one()
            if file_executable is None:
                raise FileNotFoundError
            process = subprocess.run(
                [file_executable, "--mime-type", "-b", file_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=1,
            )
            mime_type = process.stdout.strip()
            if mime_type:
                return MimeResult("file1", mime_type)
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            # file(1) command failed or is not available
            pass

    return None
