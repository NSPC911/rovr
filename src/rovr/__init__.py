def main() -> None:
    try:
        from rovr.__main__ import cli

        cli()
    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as exc:
        from rich.console import Console

        if isinstance(exc, NotImplementedError):
            Console(stderr=True).print_exception(
                width=None, extra_lines=1, max_frames=1, show_locals=False
            )
        else:
            Console(stderr=True).print_exception(
                width=None, extra_lines=2, show_locals=True
            )
