def get_candidates(path_str: str) -> list[str]:
    import os

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

    if os.path.exists(path_str) and os.path.isdir(path_str):
        # Case 3: Path ends with "/" - list contents of that directory (directories only)
        if path_str.endswith(("/", "\\")):
            items = []
            for item in sorted(os.listdir(path_str), key=str.lower):
                if os.path.isdir(os.path.join(path_str, item)):
                    items.append(item + "/")
            return items

        # Check if it's an exact directory match
        if os.path.exists(path_str) and os.path.isdir(path_str):
            return [path_str.split("/")[-1] + "/"]
    return []


def test_get_candidates() -> None:
    assert get_candidates("") == ["C:/", "D:/"]
    assert get_candidates("C") == ["C:/"]
    assert get_candidates("C:") == ["C:/"]
    assert get_candidates("C:/") == [
        "$Recycle.Bin/",
        "Documents and Settings/",
        "Drivers/",
        "inetpub/",
        "PerfLogs/",
        "ProcLogs/",
        "Program Files/",
        "Program Files (x86)/",
        "ProgramData/",
        "Recovery/",
        "System Volume Information/",
        "Users/",
        "Windows/",
    ]
    assert get_candidates("C:/Users/notso/Git/i") == [
        "100k_files/",
        "aio/",
        "BedrockTweaks/",
        "Kitty-Tools/",
        "noi/",
        "NSPC911/",
        "omp-test/",
        "PowerShellEditorServices/",
        "rovr.dist/",
        "superfile/",
        "we-ascii-clouds/",
        "yazi/",
    ]
    assert get_candidates("C:/Users/notso/Git/NSPC911") == ["NSPC911/"]
    assert get_candidates("C:/Users/notso/Git/NSPC911/") == [
        "bongo-cat/",
        "dotfiles/",
        "forks/",
        "le-bucket/",
        "NSPC911/",
        "nspc911.github.io/",
        "rovr/",
        "rowelix/",
        "test/",
        "textual-chafa/",
        "textual-trials/",
        "themes/",
        "tomltest/",
        "zcoop/",
    ]


if __name__ == "__main__":
    test_get_candidates()
