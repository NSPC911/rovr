def get_candidates(path_str: str) -> list[str]:
    from os import listdir, path

    # Case 1: nothing
    if not path_str:
        return ["/"]

    # Case 2: list directories
    if path.exists(path_str) and path.isdir(path_str):
        if path_str.endswith("/"):
            return [
                item + "/"
                for item in sorted(listdir(path_str), key=str.lower)
                if path.isdir(path.join(path_str, item))
            ]

        # Case 3: exact directory match
        path_str = path.realpath(path.expanduser(path_str))
        return [path_str.rstrip("/").split("/")[-1] + "/"]
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


if __name__ == "__main__":
    test_get_candidates()
