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


class ArchiveScreenReturnType(NamedTuple):
    path: str
    algo: Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "tar.zst"]
    level: int
