from typing import Literal, TypeAlias, TypedDict

SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str
