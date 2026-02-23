import multiprocessing
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from multiprocessing.connection import Connection

from PIL import Image
from PIL.Image import Image as PILImage

from rovr.functions.utils import should_cancel
from rovr.variables.constants import config

RESAMPLING_METHOD = {
    "nearest": Image.Resampling.NEAREST,
    "lanczos": Image.Resampling.LANCZOS,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "box": Image.Resampling.BOX,
    "hamming": Image.Resampling.HAMMING,
}.get(config["interface"]["image_viewer"]["resampling"], Image.Resampling.NEAREST)
MAX_SIZE: tuple[int, int] = tuple(config["interface"]["image_viewer"]["max_size"])  # ty: ignore


def _depalette(image: Image.Image) -> Image.Image:
    """Convert paletted images to RGBA

    Returns:
        The original image, or an RGBA-converted copy if paletted.
    """
    if image.mode in ("P", "PA"):
        return image.convert("RGBA")
    return image


def resample_worker(
    args: tuple[bytes, str, tuple[int, int], tuple[int, int], int],
) -> tuple[bytes, str, tuple[int, int]]:
    """Resample an image from raw pixel bytes.

    Returns:
        Tuple containing resampled image bytes, mode, and size.
    """
    image_data, image_mode, image_size, max_sz, resample_method = args
    img = Image.frombytes(image_mode, image_size, image_data)
    img.thumbnail(max_sz, resample=Image.Resampling(resample_method))
    return (img.tobytes(), img.mode, img.size)


def resample_bytes_worker(
    conn: Connection,
    image_data: bytes,
    image_mode: str,
    image_size: tuple[int, int],
    max_sz: tuple[int, int],
    resample_method: int,
) -> None:
    """Resample an image from raw pixel bytes."""
    try:
        conn.send(
            resample_worker((
                image_data,
                image_mode,
                image_size,
                max_sz,
                resample_method,
            ))
        )
    except Exception as exc:
        conn.send(exc)
    finally:
        conn.close()


def resample_file_worker(
    conn: Connection,
    file_path: str,
    max_size: tuple[int, int],
    resample_method: int,
) -> None:
    """Open a file, resample it, and send the result back."""
    try:
        with Image.open(file_path) as img:
            img.load()
            pil = img.copy()
        pil = _depalette(pil)
        pil.thumbnail(max_size, resample=Image.Resampling(resample_method))
        conn.send((pil.tobytes(), pil.mode, pil.size))
    except Exception as exc:
        conn.send(exc)
    finally:
        conn.close()


def _await_resample_process(
    proc: multiprocessing.Process,
    parent_conn: multiprocessing.connection.Connection,
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
    ordered_results: list[tuple[bytes, str, tuple[int, int]] | None] = [None] * len(
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
    except BaseException:
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
            MAX_SIZE,
            int(RESAMPLING_METHOD),
        ))
    executor = ProcessPoolExecutor(max_workers=_get_resample_pool_size(len(payloads)))
    try:
        futures = {
            executor.submit(resample_worker, payload): index
            for index, payload in enumerate(payloads)
        }
    except BaseException:
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
            MAX_SIZE,
            int(RESAMPLING_METHOD),
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
        args=(child_conn, file_path, MAX_SIZE, int(RESAMPLING_METHOD)),
    )
    proc.start()
    child_conn.close()

    result = _await_resample_process(proc, parent_conn)
    if result is None:
        return None
    data, mode, size = result
    return Image.frombytes(mode, size, data)
