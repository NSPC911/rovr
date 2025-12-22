import os
from binascii import unhexlify

import puremagic
import ujson


def _magic_data(
    filename: os.PathLike | str = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "magic_data.json"
    ),
) -> tuple[
    list[puremagic.PureMagic],
    list[puremagic.PureMagic],
    list[puremagic.PureMagic],
    dict[bytes, list[puremagic.PureMagic]],
]:
    """Read the magic file"""  # noqa: DOC201
    with open(filename, encoding="utf-8") as f:
        data = ujson.load(f)
    headers = sorted(
        (puremagic._create_puremagic(x) for x in data["headers"]),
        key=lambda x: x.byte_match,
    )
    footers = sorted(
        (puremagic._create_puremagic(x) for x in data["footers"]),
        key=lambda x: x.byte_match,
    )
    extensions = [puremagic._create_puremagic(x) for x in data["extension_only"]]
    multi_part_extensions = {}
    for file_match, option_list in data["multi-part"].items():
        multi_part_extensions[unhexlify(file_match.encode("ascii"))] = [
            puremagic._create_puremagic(x) for x in option_list
        ]
    return headers, footers, extensions, multi_part_extensions


puremagic._magic_data = _magic_data
