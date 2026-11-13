from __future__ import annotations

import os
import pickle
from io import BytesIO
from typing import Any

from PIL import Image
from PIL.Image import Image as PILImage
from rich.text import Text

from rovr.variables.maps import RovrVars

preview_loc = os.path.realpath(os.path.join(RovrVars.ROVRTEMP, "previews"))


def in_preview_loc(path_str: str) -> bool:
    return os.path.commonpath([os.path.realpath(path_str), preview_loc]) == preview_loc


def _cache_path(
    realpath: str,
    preview_type: str,
    stat_res: os.stat_result,
    sig: tuple[str, str],
    extra: Any = None,
) -> str:
    from hashlib import blake2b

    hash = blake2b(
        (
            f"{realpath}:{preview_type}:{stat_res.st_mtime_ns}:"
            f"{stat_res.st_size}:{sig[0]}:{sig[1]}:{extra}"
        ).encode(),
        digest_size=16,
    ).hexdigest()
    if os.path.exists(preview_loc) and not os.path.isdir(preview_loc):
        os.remove(preview_loc)
    if not os.path.exists(preview_loc):
        os.makedirs(preview_loc, exist_ok=True)
    return os.path.join(preview_loc, hash)


def load(
    realpath: str,
    preview_type: str,
    stat_res: os.stat_result,
    sig: tuple[str, str],
    extra: Any = None,
    pass_as: type[Any] = bytes,
) -> Any | None:

    # before we hash, check if file in the cache folder, if not, return None
    if in_preview_loc(realpath):
        return None

    cache_path = _cache_path(realpath, preview_type, stat_res, sig, extra)
    try:
        with open(cache_path, "rb") as f:
            content = f.read()
        if pass_as is list or pass_as is dict:
            import json

            return json.loads(content.decode())
        elif pass_as is str:
            return content.decode()
        return content
    except Exception:
        pass


def save(
    realpath: str,
    preview_type: str,
    stat_res: os.stat_result,
    sig: tuple[str, str],
    data: Any,
    extra: Any = None,
) -> None:
    # same as before
    if in_preview_loc(realpath):
        return

    try:
        if isinstance(data, (dict, list)):
            import json

            data = json.dumps(
                data, ensure_ascii=False, check_circular=False, separators=(",", ":")
            ).encode()
        elif isinstance(data, str):
            data = data.encode()
        elif not isinstance(data, bytes):
            data = str(data).encode()
        with open(_cache_path(realpath, preview_type, stat_res, sig, extra), "wb") as f:
            f.write(data)
    except OSError:
        pass


def _load_image(
    file_path: str,
    preview_type: str,
    stat_res: os.stat_res,
    sig: tuple[str, str],
    extra: Any = None,
) -> PILImage | None:
    data = load(file_path, preview_type, stat_res, sig, extra)
    if data is None:
        return None
    try:
        with Image.open(BytesIO(data)) as image:
            return image.copy()
    except (OSError, ValueError):
        return None


def _save_image(
    file_path: str,
    preview_type: str,
    stat_res: os.stat_res,
    image: PILImage,
    sig: tuple[str, str],
    extra: Any = None,
) -> None:
    output = BytesIO()
    image.save(output, format="PNG")
    save(file_path, preview_type, stat_res, sig, output.getvalue(), extra)


def _load_text(
    file_path: str,
    preview_type: str,
    stat_res: os.stat_res,
    sig: tuple[str, str],
    extra: Any = None,
) -> Text | None:
    data = load(file_path, preview_type, stat_res, sig, extra)
    if data is None:
        return None
    try:
        text = pickle.loads(data)
        return text if isinstance(text, Text) else None
    except Exception:
        return None


def _save_text(
    file_path: str,
    preview_type: str,
    stat_res: os.stat_res,
    sig: tuple[str, str],
    text: Text,
    extra: Any = None,
) -> None:
    save(
        file_path,
        preview_type,
        stat_res,
        sig,
        pickle.dumps(text, protocol=5),
        extra,
    )
