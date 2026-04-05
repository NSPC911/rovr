def get_candidates(path_str: str) -> list[str]:
    import os
    from pathlib import Path

    from textual.fuzzy import Matcher

    # Case 1: Empty string - return available drives
    if not path_str:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:/"
            if os.path.exists(drive):
                drives.append(drive)
        return drives

    # Case 2: Just a drive letter (e.g., "C") or drive with colon (e.g., "C:")
    if len(path_str) <= 2 and path_str[0].isalpha():
        drive_letter = path_str[0].upper()
        drive = f"{drive_letter}:/"
        if os.path.exists(drive):
            return [drive]
        return []

    # Case 3: Path ends with "/" - list contents of that directory (directories only)
    if path_str.endswith("/"):
        p = Path(path_str)
        if p.exists() and p.is_dir():
            items = []
            for item in sorted(p.iterdir()):
                if item.is_dir():
                    items.append(item.name)
            return items
        return []

    # Case 4: Path doesn't end with "/" - either exact match or partial completion
    p = Path(path_str)

    # Check if it's an exact directory match
    if p.exists() and p.is_dir():
        return [path_str.split("/")[-1] + "/"]

    # Otherwise, it's a partial path - use fuzzy matching to find items in parent directory
    parent = p.parent
    partial_name = p.name

    if parent.exists() and parent.is_dir():
        # Get all items in parent directory
        all_items = [item.name for item in parent.iterdir()]

        # Use fuzzy matcher to find matches
        matcher = Matcher(partial_name)
        matches = [(matcher.match(item), item) for item in all_items]

        # Filter out non-matches (score 0) and sort by score (descending)
        valid_matches = [(score, item) for score, item in matches if score > 0]
        valid_matches.sort(reverse=True, key=lambda x: x[0])

        # Return matched item names
        return [item for score, item in valid_matches]

    return []


def test_get_candidates() -> None:
    assert get_candidates("") == ["C:/", "D:/"]
    assert get_candidates("C") == ["C:/"]
    assert get_candidates("C:") == ["C:/"]
    assert get_candidates("C:/") == [
        "$Recycle.Bin",
        "Documents and Settings",
        "Drivers",
        "inetpub",
        "PerfLogs",
        "ProcLogs",
        "Program Files",
        "Program Files (x86)",
        "ProgramData",
        "Recovery",
        "System Volume Information",
        "Users",
        "Windows",
    ]
    assert get_candidates("C:/Users/notso/Git/i") == [
        "100k_files",
        "aio",
        "Kitty-Tools",
        "noi",
        "PowerShellEditorServices",
        "rovr.dist",
        "superfile",
        "we-ascii-clouds",
        "yazi",
    ]
    assert get_candidates("C:/Users/notso/Git/NSPC911") == ["NSPC911/"]
    assert get_candidates("C:/Users/notso/Git/NSPC911/") == [
        "bongo-cat",
        "dotfiles",
        "forks",
        "le-bucket",
        "NSPC911",
        "nspc911.github.io",
        "rovr",
        "rowelix",
        "test",
        "textual-chafa",
        "textual-trials",
        "themes",
        "tomltest",
        "zcoop",
    ]


if __name__ == "__main__":
    test_get_candidates()
