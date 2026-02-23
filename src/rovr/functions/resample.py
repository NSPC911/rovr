from multiprocessing.connection import Connection

from PIL import Image


def resample_bytes_worker(
    conn: Connection,
    image_data: bytes,
    image_mode: str,
    image_size: tuple[int, int],
    max_sz: tuple[int, int],
    resample_method: int,
) -> None:
    """Resample an image from raw pixel bytes."""
    img = Image.frombytes(image_mode, image_size, image_data)
    img.thumbnail(max_sz, resample=Image.Resampling(resample_method))
    conn.send((img.tobytes(), img.mode, img.size))
    conn.close()


def resample_file_worker(
    conn: Connection,
    file_path: str,
    max_sz: tuple[int, int],
    resample_method: int,
) -> None:
    """Open a file, resample it, and send the result back."""
    try:
        with Image.open(file_path) as img:
            img.load()
            pil = img.copy()
        pil.thumbnail(max_sz, resample=Image.Resampling(resample_method))
        conn.send((pil.tobytes(), pil.mode, pil.size))
    except Exception as exc:
        conn.send(exc)
    conn.close()
