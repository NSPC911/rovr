import stat
import time
from contextlib import suppress
from datetime import datetime
from os import DirEntry, lstat, path, walk

from textual import events, on, work
from textual.containers import VerticalGroup, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Static
from textual.worker import WorkerState

from rovr.functions import utils
from rovr.functions.path import is_hidden_file
from rovr.variables.constants import config
from rovr.variables.maps import SPINNER


class MetadataContainer(VerticalScroll):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_path: str | None = None
        self._size_worker = None
        self._update_task = None
        self._queued_task = None
        self._queued_task_args: None | DirEntry = None

    def info_of_dir_entry(self, dir_entry: DirEntry, type_string: str) -> str:
        """Get the permission line from a given DirEntry object
        Args:
            dir_entry (DirEntry): The nt.DirEntry class
            type_string (str): The type of file. It should already be handled.
        Returns:
            str: A permission string.
        """
        try:
            file_stat = lstat(dir_entry.path)
        except (OSError, FileNotFoundError):
            return "?????????"
        mode = file_stat.st_mode

        permission_string = ""
        match type_string:
            case "Symlink":
                permission_string = "l"
            case "Directory":
                permission_string = "d"
            case "Junction":
                permission_string = "j"
            case "File":
                permission_string = "-"
            case "Unknown":
                return "???????"

        permission_string += "r" if mode & stat.S_IRUSR else "-"
        permission_string += "w" if mode & stat.S_IWUSR else "-"
        permission_string += "x" if mode & stat.S_IXUSR else "-"

        permission_string += "r" if mode & stat.S_IRGRP else "-"
        permission_string += "w" if mode & stat.S_IWGRP else "-"
        permission_string += "x" if mode & stat.S_IXGRP else "-"

        permission_string += "r" if mode & stat.S_IROTH else "-"
        permission_string += "w" if mode & stat.S_IWOTH else "-"
        permission_string += "x" if mode & stat.S_IXOTH else "-"
        return permission_string

    def any_in_queue(self) -> bool:
        if self._queued_task is not None:
            self._queued_task(self._queued_task_args)
            self._queued_task, self._queued_task_args = None, None
            return True
        return False

    def update_metadata(self, dir_entry: DirEntry) -> None:
        """
        Debounce the update, because some people can be speed travellers
        Args:
            dir_entry (DirEntry): The nt.DirEntry object
        """
        if any(
            worker.is_running
            and worker.node is self
            and worker.name == "_perform_update"
            for worker in self.app.workers
        ):
            self._queued_task = self._perform_update
            self._queued_task_args = dir_entry
        else:
            self._perform_update(dir_entry)

    @work(thread=True)
    def _perform_update(self, dir_entry: DirEntry) -> None:
        """
        After debouncing the update
        Args:
            dir_entry (DirEntry): The nt.DirEntry object
        """
        if self.any_in_queue():
            return
        if not path.exists(dir_entry.path):
            self.app.call_from_thread(self.remove_children)
            self.app.call_from_thread(
                self.mount, Static("Item not found or inaccessible.")
            )
            return

        type_str = "Unknown"
        if dir_entry.is_junction():
            type_str = "Junction"
        elif dir_entry.is_symlink():
            type_str = "Symlink"
        elif dir_entry.is_dir():
            type_str = "Directory"
        elif dir_entry.is_file():
            type_str = "File"
        file_info = self.info_of_dir_entry(dir_entry, type_str)
        # got the type, now we follow
        file_stat = dir_entry.stat()
        is_hidden = is_hidden_file(dir_entry.path)

        values_list = []
        for field in config["metadata"]["fields"]:
            match field:
                case "type":
                    values_list.append(Static(type_str))
                case "permissions":
                    values_list.append(Static(file_info))
                case "hidden":
                    values_list.append(Static("Yes" if is_hidden else "No"))
                case "size":
                    values_list.append(
                        Static(
                            utils.natural_size(
                                file_stat.st_size,
                                config["metadata"]["filesize_suffix"],
                                config["metadata"]["filesize_decimals"],
                            )
                            if type_str == "File"
                            else "--",
                            id="metadata-size",
                        )
                    )
                case "modified":
                    values_list.append(
                        Static(
                            datetime.fromtimestamp(file_stat.st_mtime).strftime(
                                config["metadata"]["datetime_format"]
                            )
                        )
                    )
                case "accessed":
                    values_list.append(
                        Static(
                            datetime.fromtimestamp(file_stat.st_atime).strftime(
                                config["metadata"]["datetime_format"]
                            )
                        )
                    )
                case "created":
                    values_list.append(
                        Static(
                            datetime.fromtimestamp(file_stat.st_ctime).strftime(
                                config["metadata"]["datetime_format"]
                            )
                        )
                    )
        values = VerticalGroup(*values_list, id="metadata-values")

        try:
            for index, child_widget in enumerate(
                self.query_one("#metadata-values").children
            ):
                self.app.call_from_thread(
                    child_widget.update, values_list[index].content
                )
        except NoMatches:
            self.app.call_from_thread(self.remove_children)
            keys_list = []
            for field in config["metadata"]["fields"]:
                match field:
                    case "type":
                        keys_list.append(Static("Type"))
                    case "permissions":
                        keys_list.append(Static("Permissions"))
                    case "hidden":
                        keys_list.append(Static("Hidden"))
                    case "size":
                        keys_list.append(Static("Size"))
                    case "modified":
                        keys_list.append(Static("Modified"))
                    case "accessed":
                        keys_list.append(Static("Accessed"))
                    case "created":
                        keys_list.append(Static("Created"))
            keys = VerticalGroup(*keys_list, id="metadata-keys")
            self.app.call_from_thread(self.mount, keys, values)
        self.current_path = dir_entry.path
        if type_str == "Directory" and self.has_focus:
            self._size_worker = self.calculate_folder_size(dir_entry.path)
        if self.any_in_queue():
            return
        else:
            self._queued_task = None

    @work(thread=True)
    async def calculate_folder_size(self, folder_path: str) -> None:
        """Calculate the size of a folder and update the metadata."""
        size_widget = self.query_one("#metadata-size", Static)
        self.app.call_from_thread(size_widget.update, "Calculating...")

        total_size = 0
        spinner_index = -1
        last_update_time = time.monotonic()
        try:
            for dirpath, _, filenames in walk(folder_path):
                for f in filenames:
                    if self._size_worker is None or self._size_worker.is_cancelled:
                        return
                    fp = path.join(dirpath, f)
                    if not path.islink(fp):
                        with suppress(OSError, FileNotFoundError):
                            total_size += lstat(fp).st_size
                if time.monotonic() - last_update_time > 0.25:
                    spinner_index = spinner_index + 1 if spinner_index // 3 == 0 else 0
                    self.app.call_from_thread(
                        size_widget.update,
                        f"{utils.natural_size(total_size, config['metadata']['filesize_suffix'], config['metadata']['filesize_decimals'])} {SPINNER[spinner_index]}",
                    )
                    last_update_time = time.monotonic()
        except (OSError, FileNotFoundError):
            self.app.call_from_thread(size_widget.update, "Error")
            return

        if not self._size_worker.is_cancelled:
            self.app.call_from_thread(
                size_widget.update,
                utils.natural_size(
                    total_size,
                    config["metadata"]["filesize_suffix"],
                    config["metadata"]["filesize_decimals"],
                ),
            )

    @on(events.Focus)
    def on_focus(self) -> None:
        if self.current_path and path.isdir(self.current_path):
            if self._size_worker:
                return
            self._size_worker = self.calculate_folder_size(self.current_path)

    @on(events.Blur)
    def on_blur(self) -> None:
        if self._size_worker is None or self.app.app_blurred:
            return
        elif self._size_worker.state == WorkerState.SUCCESS:
            self._size_worker = None
        else:
            self._size_worker.cancel()
            self._size_worker = None
            self.set_timer(
                0.1, lambda: self.query_one("#metadata-size", Static).update("--")
            )
