def get_candidates(path_str: str) -> list[str]:
    from os import listdir, path

    if not path_str:
        return ["/"]

    if path_str.endswith("/"):
        if path.exists(path_str) and path.isdir(path_str):
            return [
                item
                for item in sorted(listdir(path_str), key=str.lower)
                if path.isdir(path.join(path_str, item))
            ]
        return []

    path_str = path.realpath(path.expanduser(path_str))
    if path.exists(path_str) and path.isdir(path_str):
        return [path_str.split("/")[-1] + "/"]

    parent = path.dirname(path_str)
    items = []

    if path.exists(parent) and path.isdir(parent):
        for item in sorted(listdir(parent), key=str.lower):
            if path.isdir(path.join(parent, item)):
                items.append(item + "/")
        return sorted(items, key=str.lower)
    return []


def test_get_candidates() -> None:
    assert get_candidates("") == ["/"]
    assert get_candidates("/") == [
        ".snapshots",
        "bin",
        "boot",
        "dev",
        "etc",
        "home",
        "lib",
        "lib64",
        "mnt",
        "opt",
        "proc",
        "root",
        "run",
        "sbin",
        "srv",
        "sys",
        "tmp",
        "usr",
        "var",
    ]
    assert get_candidates("/home/nspc911/Downloads") == ["Downloads/"]


if __name__ == "__main__":
    test_get_candidates()
