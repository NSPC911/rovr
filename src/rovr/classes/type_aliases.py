import os
import sys
from typing import Literal, TypeAlias, TypedDict

SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]

# windows needs nt, because os.scandir returns
# nt.DirEntry instead of os.DirEntry on
# windows. weird, yes, but I can't do anything
if sys.platform == "win32":
    import nt

    DirEntryType: TypeAlias = os.DirEntry | nt.DirEntry
    DirEntryTypes = (os.DirEntry, nt.DirEntry)
else:
    DirEntryType: TypeAlias = os.DirEntry
    DirEntryTypes = os.DirEntry


class BarPanicDismissible(TypedDict):
    message: str
    subtitle: str


class BarPanicNotify(TypedDict):
    message: str
    title: str
