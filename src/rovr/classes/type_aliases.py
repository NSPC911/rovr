from typing import Literal, TypeAlias, TypedDict

SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]

KeysConfig: TypeAlias = dict[str, dict[str, str]]


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str
