from collections import OrderedDict, deque
from typing import TypedDict

from rovr.variables.constants import config


class SessionOptionDict(TypedDict):
    name: str
    "Name of the option"
    index: int
    "Index of the option. Used as a fallback when `name` doesn't exist"


# What is textual reactive?
class SessionManager:
    """Manages session-related variables.

    Attributes:
        directories (deque[str]): The visited directories, capped at
            `settings.history_size` entries. The closer it is to index 0, the
            older it is; once full, appending evicts the oldest entry.
        historyIndex (int): The index of the session in the directories.
            This can be a number between 0 and the length of the list - 1,
            inclusive.
        lastHighlighted (OrderedDict[str, SessionOptionDict]): A mapping of directory
                                 paths to the index of the last highlighted item, capped at
                                 `settings.last_highlighted_size` entries (least-recently-used
                                 eviction). If a directory is not in the dictionary, the
                                 default is 0. Use `remember_highlight` to write to it.
        selectMode (bool): Whether select mode is enabled for that directory.
        selectedItems (list[SessionOptionDict]): A list of selected items within the
                                                                      current directory
        search (str): The current search string.
    """

    def __init__(self) -> None:
        self.directories: deque[str] = deque(maxlen=config["settings"]["history_size"])
        self.historyIndex: int = 0
        self.lastHighlighted: OrderedDict[str, SessionOptionDict] = OrderedDict()
        self.selectMode: bool = False
        self.selectedItems: list[SessionOptionDict] = []
        self.search: str = ""

    def remember_highlight(self, cwd: str, value: SessionOptionDict) -> None:
        """Record the last-highlighted item for a directory, evicting the
        least-recently-used entry once `settings.last_highlighted_size` is exceeded.

        Args:
            cwd (str): The directory the highlight belongs to.
            value (SessionOptionDict): The highlighted item's name/index.
        """
        self.lastHighlighted[cwd] = value
        self.lastHighlighted.move_to_end(cwd)
        max_size = config["settings"]["last_highlighted_size"]
        while len(self.lastHighlighted) > max_size:
            self.lastHighlighted.popitem(last=False)
