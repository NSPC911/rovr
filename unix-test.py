def get_candidates(path_str: str) -> list[str]:
    from pathlib import Path

    from textual.fuzzy import Matcher

    if not path_str:
        return ["/"]

    if path_str.endswith("/"):
        p = Path(path_str)
        if p.exists() and p.is_dir():
            return [item.name for item in sorted(p.iterdir()) if item.is_dir()]
        return []

    p = Path(path_str)

    if p.exists() and p.is_dir():
        return [path_str.split("/")[-1] + "/"]

    parent = p.parent
    partial_name = p.name

    if parent.exists() and parent.is_dir():
        all_items = [item.name for item in parent.iterdir() if item.is_dir()]

        matcher = Matcher(partial_name)
        matches = [(matcher.match(item), item) for item in all_items]

        valid_matches = [(score, item) for score, item in matches if score > 0]
        valid_matches.sort(reverse=True, key=lambda x: x[0])

        return [item for score, item in valid_matches]

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
    assert get_candidates("/home/nspc911/lo") == [
        ".local",
        "Downloads",
        ".copilot",
    ]
    assert get_candidates("/home/nspc911/Downloads") == ["Downloads/"]


if __name__ == "__main__":
    test_get_candidates()
