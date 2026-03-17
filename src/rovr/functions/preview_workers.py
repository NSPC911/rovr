# this isn't quite like what I do, the reason why these aren't
# in preview_utils.py is because I need to isolate the workers
# from anything related to the config, else it will keep reimporting
# it and hence tanking preview time, and also corrupt stdout

from multiprocessing.connection import Connection

from PIL import Image


def _depalette(image: Image.Image) -> Image.Image:
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
