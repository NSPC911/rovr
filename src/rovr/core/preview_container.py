import asyncio
import asyncio.subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from os import path
from typing import ClassVar

import textual_image.widget as timg
from PIL import UnidentifiedImageError
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Static, TextArea
from textual.worker import NoActiveWorker, Worker, WorkerCancelled, get_current_worker

from rovr.classes import Archive
from rovr.core import FileList
from rovr.variables.constants import PreviewContainerTitles, config
from rovr.variables.maps import ARCHIVE_EXTENSIONS_FULL, EXT_TO_LANG_MAP, PIL_EXTENSIONS

titles = PreviewContainerTitles()


class CustomTextArea(TextArea, inherit_bindings=False):
    BINDINGS: ClassVar[list[BindingType]] = (
        # Bindings from config
        [
            Binding(bind, "cursor_up", "Cursor up", show=False)
            for bind in config["keybinds"]["up"]
        ]
        + [
            Binding(bind, "cursor_down", "Cursor down", show=False)
            for bind in config["keybinds"]["down"]
        ]
        + [
            Binding(bind, "cursor_left", "Cursor left", show=False)
            for bind in config["keybinds"]["preview_scroll_left"]
        ]
        + [
            Binding(bind, "cursor_right", "Cursor right", show=False)
            for bind in config["keybinds"]["preview_scroll_right"]
        ]
        + [
            Binding(bind, "cursor_line_start", "Cursor line start", show=False)
            for bind in config["keybinds"]["home"]
        ]
        + [
            Binding(bind, "cursor_line_end", "Cursor line end", show=False)
            for bind in config["keybinds"]["end"]
        ]
        + [
            Binding(bind, "cursor_page_up", "Cursor page up", show=False)
            for bind in config["keybinds"]["page_up"]
        ]
        + [
            Binding(bind, "cursor_page_down", "Cursor page down", show=False)
            for bind in config["keybinds"]["page_down"]
        ]
        + [
            Binding(bind, "cursor_up(True)", "Cursor up select", show=False)
            for bind in config["keybinds"]["select_up"]
        ]
        + [
            Binding(bind, "cursor_down(True)", "Cursor down select", show=False)
            for bind in config["keybinds"]["select_down"]
        ]
        + [
            Binding(
                bind, "cursor_line_start(True)", "Cursor line start select", show=False
            )
            for bind in config["keybinds"]["select_home"]
        ]
        + [
            Binding(bind, "cursor_line_end(True)", "Cursor line end select", show=False)
            for bind in config["keybinds"]["select_end"]
        ]
        + [
            Binding(bind, "cursor_page_up(True)", "Cursor page up select", show=False)
            for bind in config["keybinds"]["select_page_up"]
        ]
        + [
            Binding(
                bind, "cursor_page_down(True)", "Cursor page down select", show=False
            )
            for bind in config["keybinds"]["select_page_down"]
        ]
        + [
            Binding(bind, "select_all", "Select all", show=False)
            for bind in config["keybinds"]["toggle_all"]
        ]
        + [
            Binding(bind, "delete_right", "Delete character right", show=False)
            for bind in config["keybinds"]["delete"]
        ]
        + [
            Binding(bind, "cut", "Cut", show=False)
            for bind in config["keybinds"]["cut"]
        ]
        + [
            Binding(bind, "copy", "Copy", show=False)
            for bind in config["keybinds"]["copy"]
        ]
        + [
            Binding(bind, "paste", "Paste", show=False)
            for bind in config["keybinds"]["paste"]
        ]
        + [
            Binding(bind, "cursor_right(True)", "Select right", show=False)
            for bind in config["keybinds"]["preview_select_right"]
        ]
        + [
            Binding(bind, "cursor_left(True)", "Select left", show=False)
            for bind in config["keybinds"]["preview_select_left"]
        ]
        # Hardcoded bindings
        + [
            Binding("ctrl+left", "cursor_word_left", "Cursor word left", show=False),
            Binding("ctrl+right", "cursor_word_right", "Cursor word right", show=False),
            Binding(
                "shift+left", "cursor_left(True)", "Cursor left select", show=False
            ),
            Binding(
                "shift+right", "cursor_right(True)", "Cursor right select", show=False
            ),
            Binding(
                "ctrl+shift+left",
                "cursor_word_left(True)",
                "Cursor left word select",
                show=False,
            ),
            Binding(
                "ctrl+shift+right",
                "cursor_word_right(True)",
                "Cursor right word select",
                show=False,
            ),
            Binding("f6", "select_line", "Select line", show=False),
        ]
    )


class PreviewContainer(Container):
    @dataclass
    class SetLoading(Message):
        """
        Message sent to turn this widget into the loading state
        """

        to: bool
        """What to set the `loading` attribute to"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pending_preview_path: str | None = None
        self._current_content: str | list[str] | None = None
        self._current_file_path = None
        self._initial_height = self.size.height
        self._file_type: str = "none"

    def compose(self) -> ComposeResult:
        yield Static(config["interface"]["preview_text"]["start"], classes="wrap")

    def on_preview_container_set_loading(self, event: SetLoading) -> None:
        self.loading = event.to

    def has_child(self, selector: str) -> bool:
        """
        Check for whether this element contains this selector or not
        Args:
            selector(str): the selector to test

        Returns:
            bool: whether the selector is valid
        """
        try:
            self.query_one(selector)
            return True
        except NoMatches:
            return False

    async def show_image_preview(self) -> None:
        try:
            worker = get_current_worker()
        except RuntimeError:
            worker = None
        if worker and not worker.is_running:
            return

        if not self.has_child("#image_preview"):
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

            if worker and not worker.is_running:
                return

            try:
                await self.mount(
                    timg.__dict__[config["settings"]["image_protocol"] + "Image"](
                        self._current_file_path,
                        id="image_preview",
                        classes="inner_preview",
                    )
                )
                self.query_one("#image_preview").can_focus = True
            except FileNotFoundError:
                if worker and not worker.is_running:
                    return
                await self.mount(
                    CustomTextArea(
                        id="text_preview",
                        show_line_numbers=False,
                        soft_wrap=True,
                        read_only=True,
                        text=config["interface"]["preview_text"]["error"],
                        language="markdown",
                        compact=True,
                    )
                )
            except UnidentifiedImageError:
                if worker and not worker.is_running:
                    return
                await self.mount(
                    CustomTextArea(
                        id="text_preview",
                        show_line_numbers=False,
                        soft_wrap=True,
                        read_only=True,
                        text="Cannot render image (is the encoding wrong?)",
                        language="markdown",
                        compact=True,
                    )
                )
        else:
            try:
                if worker and not worker.is_running:
                    return
                self.query_one("#image_preview").image = self._current_file_path
            except Exception:
                if worker and not worker.is_running:
                    return
                await self.remove_children()
                await self.show_image_preview()

        if worker and not worker.is_running:
            return
        self.border_title = titles.image

    async def show_bat_file_preview(self) -> bool:
        try:
            worker = get_current_worker()
        except RuntimeError:
            worker = None
        bat_executable = config["plugins"]["bat"]["executable"]
        command = [
            bat_executable,
            "--force-colorization",
            "--paging=never",
            "--style=numbers"
            if config["interface"]["show_line_numbers"]
            else "--style=plain",
        ]
        max_lines = self.size.height
        if max_lines > 0:
            command.append(f"--line-range=:{max_lines}")
        command.append(self._current_file_path)

        if worker and not worker.is_running:
            return False

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if worker and not worker.is_running:
                return False

            if process.returncode == 0:
                bat_output = stdout.decode("utf-8", errors="ignore")
                new_content = Text.from_ansi(bat_output)

                if worker and not worker.is_running:
                    return False

                if not self.has_child("Static"):
                    await self.remove_children()

                    if worker and not worker.is_running:
                        return False

                    await self.mount(
                        Static(new_content, id="text_preview", classes="inner_preview")
                    )
                    if worker and not worker.is_running:
                        return False
                    self.query_one(Static).can_focus = True
                else:
                    self.query_one(Static).update(new_content)
                self.query_one(Static).classes = ""

                if worker and not worker.is_running:
                    return False

                self.border_title = titles.bat
                return True
            else:
                error_message = stderr.decode("utf-8", errors="ignore")
                if worker and not worker.is_running:
                    return False
                await self.remove_children()
                self.notify(
                    error_message,
                    title="Plugins: Bat",
                    severity="warning",
                )
                return False
        except Exception as e:
            if worker and not worker.is_running:
                return False
            self.notify(str(e), title="Plugins: Bat", severity="warning")
            return False

    async def show_normal_file_preview(self) -> None:
        try:
            worker = get_current_worker()
        except RuntimeError:
            worker = None
        if worker and not worker.is_running:
            return

        text_to_display = self._current_content
        preview_full = config["settings"]["preview_full"]
        if not preview_full:
            lines = text_to_display.splitlines()
            max_lines = self.size.height
            if max_lines > 0:
                if len(lines) > max_lines:
                    lines = lines[:max_lines]
            else:
                lines = []
            max_width = self.size.width - 7
            if max_width > 0:
                processed_lines = []
                for line in lines:
                    if len(line) > max_width:
                        processed_lines.append(line[:max_width])
                    else:
                        processed_lines.append(line)
                lines = processed_lines
            text_to_display = "\n".join(lines)

        if worker and not worker.is_running:
            return

        is_special_content = self._current_content in (
            config["interface"]["preview_text"]["binary"],
            config["interface"]["preview_text"]["error"],
        )
        language = (
            "markdown"
            if is_special_content
            else EXT_TO_LANG_MAP.get(
                path.splitext(self._current_file_path)[1], "markdown"
            )
        )

        if worker and not worker.is_running:
            return

        if not self.has_child("CustomTextArea"):
            await self.remove_children()

            if worker and not worker.is_running:
                return

            await self.mount(
                CustomTextArea(
                    id="text_preview",
                    show_line_numbers=config["interface"]["show_line_numbers"],
                    soft_wrap=False,
                    read_only=True,
                    text=text_to_display,
                    language=language,
                    classes="inner_preview",
                )
            )
        else:
            text_area = self.query_one("#text_preview", CustomTextArea)
            text_area.text = text_to_display
            text_area.language = language

        if worker and not worker.is_running:
            return

        self.border_title = titles.file

    async def show_folder_preview(self, folder_path: str) -> None:
        try:
            worker = get_current_worker()
        except (RuntimeError, NoActiveWorker):
            worker = None
        if worker and not worker.is_running:
            return

        if not self.has_child("FileList"):
            await self.remove_children()

            if worker and not worker.is_running:
                return

            await self.mount(
                FileList(
                    name=folder_path,
                    classes="file-list inner_preview",
                    dummy=True,
                    enter_into=folder_path,
                )
            )

        if worker and not worker.is_running:
            return

        folder_preview = self.query_one(FileList)
        updater_worker = folder_preview.dummy_update_file_list(
            cwd=folder_path,
        )

        try:
            await updater_worker.wait()
        except WorkerCancelled:
            return

        if worker and not worker.is_running:
            return

        self.border_title = titles.folder

    async def show_archive_preview(self) -> None:
        try:
            worker = get_current_worker()
        except RuntimeError:
            worker = None
        if worker and not worker.is_running:
            return

        if not self.has_child("FileList"):
            await self.remove_children()

            if worker and not worker.is_running:
                return

            await self.mount(
                FileList(
                    classes="file-list inner_preview",
                    dummy=True,
                )
            )

        if worker and not worker.is_running:
            return

        updater_worker: Worker = self.query_one(FileList).create_archive_list(
            self._current_content
        )

        try:
            await updater_worker.wait()
        except WorkerCancelled:
            return

        if worker and not worker.is_running:
            return

        self.border_title = titles.archive

    def show_preview(self, file_path: str) -> None:
        if (
            "hide" in self.classes
            or "-nopreview" in self.screen.classes
            or "-filelistonly" in self.screen.classes
        ):
            self._pending_preview_path = file_path
            return
        self._pending_preview_path = None
        self.perform_show_preview(file_path)

    @work(exclusive=True, thread=True)
    def perform_show_preview(self, file_path: str) -> None:
        worker = get_current_worker()
        if worker and not worker.is_running:
            return
        self.post_message(self.SetLoading(True))

        if path.isdir(file_path):
            self.app.call_from_thread(self.update_ui, file_path=file_path, file_type="folder")
        else:
            if any(file_path.endswith(ext) for ext in PIL_EXTENSIONS):
                file_type = "image"
            elif any(file_path.endswith(ext) for ext in ARCHIVE_EXTENSIONS_FULL):
                file_type = "archive"
            else:
                file_type = "file"

            content = None

            if worker and not worker.is_running:
                return

            match file_type:
                case "archive":
                    try:
                        with Archive(file_path, "r") as archive:
                            all_files = []
                            for member in archive.infolist():
                                if worker and not worker.is_running:
                                    return

                                filename = getattr(
                                    member, "filename", getattr(member, "name", "")
                                )
                                is_dir_func = getattr(
                                    member, "is_dir", getattr(member, "isdir", None)
                                )
                                is_dir = (
                                    is_dir_func()
                                    if is_dir_func
                                    else filename.replace("\\", "/").endswith("/")
                                )
                                if not is_dir:
                                    all_files.append(filename)
                        content = all_files
                    except (
                        zipfile.BadZipFile,
                        tarfile.TarError,
                        ValueError,
                        FileNotFoundError,
                    ):
                        content = [config["interface"]["preview_text"]["error"]]
                case "image":
                    pass
                case _:
                    if worker and not worker.is_running:
                        return
                    # prevent files > 1mb from being
                    # read because are you stupid, why
                    # would you use rovr for that anyways
                    size = path.getsize(file_path)
                    if size > 1024 ** 2:
                        content = config["interface"]["preview_text"]["too_large"]
                    elif size == 0:
                        content = config["interface"]["preview_text"]["empty"]
                    else:
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            content = config["interface"]["preview_text"]["binary"]
                        except (FileNotFoundError, PermissionError, OSError, MemoryError):
                            content = config["interface"]["preview_text"]["error"]

            if worker and not worker.is_running:
                return

            self.app.call_from_thread(
                self.update_ui,
                file_path,
                file_type=file_type,
                content=content,
            )

        if worker and not worker.is_running:
            return
        self.call_later(lambda: self.post_message(self.SetLoading(False)))

    async def update_ui(
        self,
        file_path: str,
        file_type: str,
        content: str | list[str] | None = None,
    ) -> None:
        """
        Update the preview UI. This runs on the main thread.
        """
        self._current_file_path = file_path
        self._current_content = content

        self._file_type = file_type

        if file_type == "folder":
            await self.show_folder_preview(file_path)
        elif file_type == "image":
            await self.show_image_preview()
        elif file_type == "archive":
            await self.show_archive_preview()
        elif content is not None:
            if content in config["interface"]["preview_text"].values():
                await self.mount_special_messages()
            else:
                if (
                    config["plugins"]["bat"]["enabled"]
                    and await self.show_bat_file_preview()
                ):
                    self.log("bat success")
                else:
                    await self.show_normal_file_preview()

    async def mount_special_messages(self) -> None:
        try:
            worker = get_current_worker()
        except RuntimeError:
            worker = None
        if worker and not worker.is_running:
            return
        if self.has_child("Static"):
            self.query_one(Static).update(self._current_content)
        else:
            await self.remove_children()
            if worker and not worker.is_running:
                return
            await self.mount(Static(self._current_content))
        self.query_one(Static).can_focus = True
        self.query_one(Static).classes = "wrap"
        if worker and not worker.is_running:
            return
        self.border_title = ""

    async def on_resize(self, event: events.Resize) -> None:
        """Re-render the preview on resize if it's was rendered by batcat and height changed."""
        if (
            self.has_child("Static")
            and event.size.height != self._initial_height
        ) or self.has_child("CustomTextArea"):
            if self._current_content is not None:
                is_special_content = self._current_content in config["interface"]["preview_text"].values()
                if (
                    config["plugins"]["bat"]["enabled"]
                    and not is_special_content
                    and await self.show_bat_file_preview()
                ):
                    pass
                else:
                    await self.show_normal_file_preview()
            self._initial_height = event.size.height

    async def on_key(self, event: events.Key) -> None:
        """Check for vim keybinds."""
        if self.border_title == titles.bat or self.border_title == titles.archive:
            widget = (
                self if self.border_title == titles.bat else self.query_one(FileList)
            )
            match event.key:
                case key if key in config["keybinds"]["up"]:
                    event.stop()
                    widget.scroll_up(animate=False)
                case key if key in config["keybinds"]["down"]:
                    event.stop()
                    widget.scroll_down(animate=False)
                case key if key in config["keybinds"]["page_up"]:
                    event.stop()
                    widget.scroll_page_up(animate=False)
                case key if key in config["keybinds"]["page_down"]:
                    event.stop()
                    widget.scroll_page_down(animate=False)
                case key if key in config["keybinds"]["home"]:
                    event.stop()
                    widget.scroll_home(animate=False)
                case key if key in config["keybinds"]["end"]:
                    event.stop()
                    widget.scroll_end(animate=False)
                case key if key in config["keybinds"]["preview_scroll_left"]:
                    event.stop()
                    widget.scroll_left(animate=False)
                case key if key in config["keybinds"]["preview_scroll_right"]:
                    event.stop()
                    widget.scroll_right(animate=False)

    @on(events.Show)
    def when_become_visible(self, event: events.Show) -> None:
        if self._pending_preview_path is not None:
            pending = self._pending_preview_path
            self._pending_preview_path = None
            self.perform_show_preview(pending)
