# What is textual reactive?
class SessionManager:
    """Manages session-related variables.

    Attributes:
        directories (list[dict]): A list of dictionaries that contain a
            directory's name within. The closer it is to index 0, the
            older it is.
        historyIndex (int): The index of the session in the directories.
            This can be a number between 0 and the length of the list - 1,
            inclusive.
        lastHighlighted (dict[str, int]): A dictionary mapping directory paths
            to the index of the last highlighted item. If a directory is not
            in the dictionary, the default is 0.
        selectMode (bool): Whether select mode is enabled for that directory.
        selectedItems (list[str]): A dictionary mapping directory paths to the
            list of selected items in that directory.
        search (str): The current search string.
    """

    def __init__(self) -> None:
        # I question to myself why directories isn't a list[str]
        # but is a list[dict], so I'm down to take some PRs, because
        # I have other things that are more important.
        # TODO: use list[str] instead of list[dict] for directories
        self.directories: list[dict] = []
        self.historyIndex: int = 0
        self.lastHighlighted: dict[str, int] = {}
        self.selectMode: bool = False
        self.selectedItems: list[str] = []
        self.search: str = ""
