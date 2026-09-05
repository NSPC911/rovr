# this is one of two files in the entire repository that is written fully by AI
import argparse
import os
import re
from collections.abc import Sequence
from typing import Any, Never


def pprint(*args: Any, **kwargs: Any) -> None:
    """Print messages to the console using rich formatting."""
    from rovr import pprint

    pprint(*args, **kwargs)


def print_rich_error(message: str) -> None:
    from rich.markup import escape
    from rich.panel import Panel

    pprint(
        Panel(
            escape(message),
            title="Error",
            border_style="red bold",
            title_align="left",
            width=80,
        )
    )


class RichArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that uses rich for error reporting."""

    def print_help(self, file: Any = None) -> None:
        print_rich_help(self)

    def error(self, message: str) -> Never:
        print_rich_error(self._format_error_message(message))
        raise SystemExit(2)

    @staticmethod
    def _format_error_message(message: str) -> str:
        # argparse default errors are a bit too technical, so we'll map them to be more user-friendly
        expected_arg_match = re.match(
            r"argument (?P<option>[^:]+): expected one argument", message
        )
        if expected_arg_match:
            option_group = expected_arg_match.group("option")
            # attempt to extract the long option (e.g. --chooser-file) from a group like -c/--chooser-file
            option = next(
                (part for part in option_group.split("/") if part.startswith("--")),
                option_group.split("/")[-1],
            )
            return f"Option '{option}' requires an argument."

        # fallback to original message with capitalization if no specific mapping found
        return message[:1].upper() + message[1:] if message else "Unknown CLI error."


def _format_action_name(action: argparse.Action) -> str:
    """Format the option name(s) for the help table.
    Args:
        action: The argparse Action to format.
    Returns:
        str: represents the option name(s) for this action."""
    if action.option_strings:
        return ", ".join(action.option_strings)

    # for positional arguments
    if isinstance(action.metavar, tuple):
        return action.metavar[0] if action.metavar else action.dest.upper()
    return str(action.metavar or action.dest.upper())


def _format_action_type(action: argparse.Action) -> str:
    """Format the argument type (STRING, INTEGER, etc.) for the help table.
    Args:
        action: The argparse Action to determine the type of.
    Returns:
        str: represents the argument type (e.g. "STRING", "INTEGER", "FLOAT")."""
    if action.nargs == 0:
        return ""
    if action.metavar == action.dest:
        return ""

    action_type = action.type
    if action_type is float:
        return "FLOAT"
    if action_type is int:
        return "INTEGER"

    return "STRING"


def _iter_visible_actions(group: Any) -> list[argparse.Action]:
    """Iterate over actions in a group that are not suppressed.
    Args:
        group: The argparse ActionGroup to iterate over.
    Returns:
        list[argparse.Action]: actions that should be displayed in the help."""
    actions = []
    for action in group._group_actions:
        if action.help is argparse.SUPPRESS:
            continue
        if isinstance(action, argparse._SubParsersAction):
            actions.extend(action._choices_actions)
        else:
            actions.append(action)
    return actions


def _render_panel(
    title: str,
    actions: list[argparse.Action],
    subtitle: str = "",
    widths: tuple[int | None, int | None] = (None, None),
) -> None:
    from rich.panel import Panel
    from rich.table import Table

    if not actions:
        return

    # 3-column grid: [FLAG] [TYPE] [HELP_TEXT]
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True, width=widths[0])
    table.add_column(style="bold yellow", no_wrap=True, width=widths[1])
    table.add_column(style="default")

    for action in actions:
        help_text = action.help if isinstance(action.help, str) else ""
        table.add_row(
            _format_action_name(action),
            _format_action_type(action),
            help_text,
        )

    panel_title = title if not subtitle else f"{title} - {subtitle}"
    panel = Panel(
        table,
        title=panel_title,
        border_style="blue bold",
        title_align="left",
        width=80,
    )
    pprint(panel)


def print_rich_help(parser: argparse.ArgumentParser) -> None:
    """Print the complete help interface using rich panels."""
    pprint(" ")
    usage = parser.format_usage().removeprefix("usage: ").strip()
    pprint(f" [bold]Usage:[/] {usage}")
    pprint(" ")
    if parser.description:
        pprint(f" [dim]{parser.description}[/]")
        pprint(" ")

    ordered_titles = ["Config", "Paths", "Miscellaneous", "Dev", "Arguments"]
    ordered_titles.extend(
        group.title
        for group in parser._action_groups
        if group.title and group.title not in ordered_titles
    )
    groups = [
        group
        for title in ordered_titles
        for group in parser._action_groups
        if group.title == title
    ]
    grouped_actions = [(group, _iter_visible_actions(group)) for group in groups]
    typed_sizes = [
        (
            max(map(len, map(_format_action_name, actions))),
            max(map(len, map(_format_action_type, actions))),
        )
        for _, actions in grouped_actions
        if actions
        and any(map(_format_action_type, actions))
        and any(isinstance(action.help, str) and action.help for action in actions)
    ]
    widths = (
        max(size[0] for size in typed_sizes)
        if len({size[0] for size in typed_sizes}) > 1
        else None,
        max(size[1] for size in typed_sizes)
        if len({size[1] for size in typed_sizes}) > 1
        else None,
    )
    for group, actions in grouped_actions:
        title = group.title or ""
        _render_panel(
            title,
            actions,
            subtitle=(group.description or "") if title == "Paths" else "",
            widths=widths
            if any(map(_format_action_type, actions))
            and any(isinstance(action.help, str) and action.help for action in actions)
            else (None, None),
        )


class RichPanelHelpAction(argparse.Action):
    """argparse Action that triggers the custom rich help display."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        print_rich_help(parser)
        parser.exit()


def existing_dir(value: str) -> str:
    """argparse type function to validate that a directory exists.
    Args:
        value: The directory path to validate.
    Returns:
        str: The normalized directory path if it exists.
    Raises:
        argparse.ArgumentTypeError: If the directory does not exist."""
    from pathlib import Path

    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Directory does not exist: {value}")
    elif not path.is_dir():
        raise argparse.ArgumentTypeError(f"Not a directory: {value}")
    return path.as_posix()


def eager_set_folder(config_folder: str | None) -> None:
    if not config_folder:
        return
    config_root = os.path.realpath(config_folder).replace("\\", "/")
    os.environ["ROVR_CONFIG_FOLDER"] = config_root

    from rovr.variables.maps import RovrVars

    RovrVars.ROVRCONFIG = config_root
    RovrVars.ROVRSTATE = os.path.join(config_root, "cache").replace("\\", "/")
