import click
from rich.console import Console
from rich.table import Table

from rovr.functions.icons import get_icon_for_file, get_icon_for_folder
from rovr.variables.maps import FILE_MAP, FILES_MAP, FOLDER_MAP, ICONS

console = Console()


def print_file_extensions() -> None:
    """Print all file extensions with their icons and colors"""
    table = Table(title="File Extensions", padding=(0, 2), show_lines=False)
    table.add_column("Icon", width=4, justify="center")
    table.add_column("Extension", width=None, justify="center")
    table.add_column("Color", width=9, justify="center")

    sorted_extensions = sorted(FILE_MAP.keys())

    for extension in sorted_extensions:
        test_file = f"test{extension}"
        icon, color = get_icon_for_file(test_file)
        icon_type = FILE_MAP[extension]

        table.add_row(
            f"[{color}]{icon}[/{color}]",
            f"{extension} ({icon_type})",
            f"[{color}]{color}[/{color}]",
        )

    console.print(table)


def print_special_filenames() -> None:
    """Print special filenames with their icons and colors"""
    table = Table(title="Special Filenames", padding=(0, 2), show_lines=False)
    table.add_column("Icon", width=4, justify="center")
    table.add_column("Filename", width=None, justify="center")
    table.add_column("Color", width=9, justify="center")

    sorted_filenames = sorted(FILES_MAP.keys())

    for filename in sorted_filenames:
        icon, color = get_icon_for_file(filename)
        icon_type = FILES_MAP[filename]

        table.add_row(
            f"[{color}]{icon}[/{color}]",
            f"{filename} ({icon_type})",
            f"[{color}]{color}[/{color}]",
        )

    console.print(table)


def print_folder_types() -> None:
    """Print folder types with their icons and colors"""
    table = Table(title="Folder Types", padding=(0, 2), show_lines=False)
    table.add_column("Icon", width=4, justify="center")
    table.add_column("Folder Name", width=None, justify="center")
    table.add_column("Color", width=9, justify="center")

    sorted_folders = sorted(FOLDER_MAP.keys())

    for folder_name in sorted_folders:
        icon, color = get_icon_for_folder(folder_name)
        icon_type = FOLDER_MAP[folder_name]

        table.add_row(
            f"[{color}]{icon}[/{color}]",
            f"{folder_name} ({icon_type})",
            f"[{color}]{color}[/{color}]",
        )

    console.print(table)


def print_default_icons() -> None:
    """Print default icons"""
    table = Table(title="Default Icons", padding=(0, 2), show_lines=False)
    table.add_column("Icon", width=4, justify="center")
    table.add_column("Type", width=None, justify="center")
    table.add_column("Color", width=15, justify="center")

    file_icon, file_color = ICONS["file"]["default"]
    table.add_row(
        f"[{file_color}]{file_icon}[/{file_color}]",
        "[white]Default File[/white]",
        f"[{file_color}]{file_color}[/{file_color}]",
    )

    folder_icon, folder_color = ICONS["folder"]["default"]
    table.add_row(
        f"[{folder_color}]{folder_icon}[/{folder_color}]",
        "[white]Default Folder[/white]",
        f"[{folder_color}]{folder_color}[/{folder_color}]",
    )

    console.print(table)


@click.command()
@click.option("--default", "default", type=bool, is_flag=True, default=False)
@click.option("--files", "files", type=bool, is_flag=True, default=False)
@click.option("--special", "special", type=bool, is_flag=True, default=False)
@click.option("--folder", "folder", type=bool, is_flag=True, default=False)
@click.option("--all", "all_options", type=bool, is_flag=True, default=False)
def main(
    default: bool, files: bool, special: bool, folder: bool, all_options: bool
) -> None:
    """Display all icons used in the rovr file manager"""
    console.print("[bold magenta]Rovr Icon Display[/bold magenta]")
    console.print(
        "Displaying all possible file extensions, special filenames, and folder types with their icons\n"
    )

    if default or all_options:
        print_default_icons()
    if files or all_options:
        print_file_extensions()
    if special or all_options:
        print_special_filenames()
    if folder or all_options:
        print_folder_types()


if __name__ == "__main__":
    main()
