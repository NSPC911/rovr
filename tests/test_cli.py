from rovr.__main__ import _build_parser


def test_parser_accepts_multiple_paths() -> None:
    args = _build_parser().parse_args([".", ".."])

    assert args.paths == [".", ".."]


def test_parser_accepts_check_keys() -> None:
    assert _build_parser().parse_args(["--check-keys"]).check_keys
