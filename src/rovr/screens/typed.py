from typing import Literal, TypedDict


class FileInUse(TypedDict):
    value: Literal["try_again", "cancel", "skip"]
    toggle: bool


class YesOrNo(TypedDict):
    value: bool
    toggle: bool


class CommonFileNameDoWhat(TypedDict):
    value: Literal["overwrite", "rename", "skip", "cancel"]
    same_for_next: bool
