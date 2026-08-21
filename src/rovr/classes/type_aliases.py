from typing import Literal, NotRequired, TypeAlias, TypedDict

SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]


class KeyBinding(TypedDict):
    action: str
    desc: NotRequired[str]


KeysConfig: TypeAlias = dict[str, dict[str, KeyBinding | str]]


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str
