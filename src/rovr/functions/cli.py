import argparse
import os
from collections.abc import Sequence
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

pprint = Console().print


def _format_action_name(action: argparse.Action) -> str:
    if action.option_strings:
        return ", ".join(action.option_strings)

    if isinstance(action.metavar, tuple):
        return action.metavar[0] if action.metavar else action.dest.upper()
    return str(action.metavar or action.dest.upper())


def _format_action_type(action: argparse.Action) -> str:
    if action.nargs == 0:
        return ""

    action_type = action.type
    if action_type is float:
        return "FLOAT"
    if action_type is int:
        return "INTEGER"

    return "STRING"


def _iter_visible_actions(group: Any) -> list[argparse.Action]:
    return [
        action
        for action in group._group_actions
        if action.help is not argparse.SUPPRESS
    ]


def _render_panel(
    title: str, actions: list[argparse.Action], subtitle: str = ""
) -> None:
    if not actions:
        return

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True, width=22)
    table.add_column(style="bold yellow", no_wrap=True, width=8)
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
    pprint(" ")
    pprint(" [bold]Usage:[/] rovr [OPTIONS] [PATH]")
    pprint(" ")
    if parser.description:
        pprint(f" [dim]{parser.description}[/]")
        pprint(" ")

    groups = {group.title: group for group in parser._action_groups}

    config_group = groups.get("Config")
    paths_group = groups.get("Paths")
    misc_group = groups.get("Miscellaneous")
    dev_group = groups.get("Dev")
    args_group = groups.get("Arguments")

    if config_group is not None:
        _render_panel("Config", _iter_visible_actions(config_group))
    if paths_group is not None:
        _render_panel(
            "Paths",
            _iter_visible_actions(paths_group),
            subtitle=(paths_group.description or ""),
        )
    if misc_group is not None:
        _render_panel("Miscellaneous", _iter_visible_actions(misc_group))
    if dev_group is not None:
        _render_panel("Dev", _iter_visible_actions(dev_group))
    if args_group is not None:
        _render_panel("Arguments", _iter_visible_actions(args_group))


class RichPanelHelpAction(argparse.Action):
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
    normalized = os.path.realpath(value.replace("\\", "/"))
    if not os.path.isdir(normalized):
        raise argparse.ArgumentTypeError(f"Directory does not exist: {value}")
    return normalized


def eager_set_folder(config_folder: str | None) -> None:
    if not config_folder:
        return

    from os import path

    from rovr.variables.maps import RovrVars

    config_root = path.realpath(config_folder.replace("\\", "/"))
    RovrVars.ROVRCONFIG = type(RovrVars).ROVRCONFIG = config_root
    RovrVars.ROVRCACHE = type(RovrVars).ROVRCACHE = path.join(
        config_root, "cache"
    ).replace("\\", "/")
