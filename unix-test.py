def get_candidates(path_str: str) -> list[str]:
    from os import listdir, path

    # Case 1: nothing
    if not path_str:
        return ["/"]

    # Case 2: list directories
    if (not path_str.endswith("/")) and path.exists(path_str) and path.isdir(path_str):
        # Case 3: exact directory match
        path_str = path.realpath(path.expanduser(path_str))
        return [path_str.rstrip("/").split("/")[-1] + "/"]

    # Case 3: list contents of parent
    parent = path.dirname(path_str)
    if path.exists(parent) and path.isdir(parent):
        return sorted(
            [
                item + "/"
                for item in listdir(parent)
                if path.isdir(path.join(parent, item))
            ],
            key=str.lower,
        )
    return []


def test_get_candidates() -> None:
    assert get_candidates("") == ["/"]
    assert get_candidates("/") == [
        ".snapshots/",
        "bin/",
        "boot/",
        "dev/",
        "etc/",
        "home/",
        "lib/",
        "lib64/",
        "mnt/",
        "opt/",
        "proc/",
        "root/",
        "run/",
        "sbin/",
        "srv/",
        "sys/",
        "tmp/",
        "usr/",
        "var/",
    ]
    assert get_candidates("/home/nspc911/Downloads") == ["Downloads/"]
    assert get_candidates("/home/nspc911/Git/n") == [
        "go-nord/",
        "NSPC911/",
        "PowerShellEditorServices/",
        "rovr-nuitka-linux-x64/",
        "simple-linux-wallpaperengine-gui/",
        "smassh/",
    ]


if __name__ == "__main__":
    test_get_candidates()
