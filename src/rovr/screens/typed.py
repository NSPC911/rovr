from typing import Literal, NamedTuple, TypedDict


class FileInUse(TypedDict):
    value: Literal["try_again", "cancel", "skip"]
    toggle: bool


class YesOrNo(TypedDict):
    value: bool
    toggle: bool


class CommonFileNameDoWhat(TypedDict):
    value: Literal["overwrite", "rename", "skip", "cancel"]
    same_for_next: bool


class ZipScreenReturnType(NamedTuple):
    path: str
    mode: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"]
    level: int
