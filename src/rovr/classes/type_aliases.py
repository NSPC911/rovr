from typing import Literal, NotRequired, TypeAlias, TypedDict


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str


class KeyBinding(TypedDict):
    action: str
    desc: NotRequired[str]


SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]

ShellRunTypes: TypeAlias = Literal["suspend", "background", "orphan"]

KeysConfig: TypeAlias = dict[str, dict[str, KeyBinding]]
