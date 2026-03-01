import os
import platform
from typing import Literal, TypeAlias

PreviewTypes: TypeAlias = Literal[
    "text", "image", "pdf", "archive", "folder", "remime", "resvg", "font", "video"
]
SortByOptions: TypeAlias = Literal[
    "name", "size", "modified", "created", "extension", "natural"
]

os_type = platform.system()

# windows needs nt, because os.scandir returns
# nt.DirEntry instead of os.DirEntry on
# windows. weird, yes, but I can't do anything
if os_type == "Windows":
    import nt

    DirEntryType: TypeAlias = os.DirEntry | nt.DirEntry
    DirEntryTypes = (os.DirEntry, nt.DirEntry)
else:
    DirEntryType: TypeAlias = os.DirEntry
    DirEntryTypes = os.DirEntry
