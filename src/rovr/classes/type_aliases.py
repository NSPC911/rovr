import os
from typing import Callable, Literal, NamedTuple, NotRequired, TypeAlias, TypedDict

KeyMap: TypeAlias = "dict[str, KeyBinding | KeyMap | str]"


SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]

ShellRunTypes: TypeAlias = Literal["suspend", "background", "orphan"]

KeysConfig: TypeAlias = dict[str, KeyMap]

type CacheSource = tuple[str, os.stat_result, tuple[str, str]]

CallableNone: TypeAlias = Callable[[], None]


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str


class KeyBinding(TypedDict):
    action: str
    desc: NotRequired[str]


class Command(NamedTuple):
    command: str | list[str]
    run_type: ShellRunTypes


class RaiseNow(object): ...
