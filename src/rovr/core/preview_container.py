import asyncio
import asyncio.subprocess
import tarfile
import zipfile
from os import path
from typing import ClassVar

import textual_image.widget as timg
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.widgets import Static, TextArea

from rovr.classes import Archive
from rovr.core import FileList
from rovr.variables.constants import PreviewContainerTitles, config
from rovr.variables.maps import ARCHIVE_EXTENSIONS, EXT_TO_LANG_MAP, PIL_EXTENSIONS

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
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._queued_task = None
        self._queued_task_args: str | None = None
        self._current_content: str | list[str] | None = None
        self._current_file_path = None
        self._is_image = False
        self._is_archive = False
        self._initial_height = self.size.height
        self._current_preview_type = "none"

    def compose(self) -> ComposeResult:
        # for some unknown reason, it started causing KeyErrors
        # and I just cannot catch the exception
        # yield TextArea(
        #     id="text_preview",
        #     show_line_numbers=True,
        #     soft_wrap=True,
        #     read_only=True,
        #     text=config["interface"]["preview_start"],
        #     language="markdown",
        #     compact=True
        # )
        yield Static(config["interface"]["preview_start"])

    async def _show_image_preview(self) -> None:
        """Ensure image preview widget exists and is updated."""
        if self._current_preview_type != "image":
            self._current_preview_type = "none"
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

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
                await self.mount(
                    CustomTextArea(
                        id="text_preview",
                        show_line_numbers=False,
                        soft_wrap=True,
                        read_only=True,
                        text=config["interface"]["preview_error"],
                        language="markdown",
                        compact=True,
                    )
                )
            self._current_preview_type = "image"
        else:
            try:
                self.query_one("#image_preview").image = self._current_file_path
            except Exception:
                self._current_preview_type = "none"
                # re-make the widget itself
                await self._show_image_preview()
        self.border_title = titles.image

    async def _show_bat_file_preview(self) -> bool:
        """Render file preview using bat, updating in place if possible.
        Returns:
            bool: whether or not the action was successful"""
        bat_executable = config["plugins"]["bat"]["executable"]
        preview_full = config["settings"]["preview_full"]
        command = [
            bat_executable,
            "--force-colorization",
            "--paging=never",
            "--style=numbers"
            if config["plugins"]["bat"]["show_line_numbers"]
            else "--style=plain",
        ]
        if not preview_full:
            max_lines = self.size.height
            if max_lines > 0:
                command.append(f"--line-range=:{max_lines}")
        command.append(self._current_file_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                bat_output = stdout.decode("utf-8", errors="ignore")
                new_content = Text.from_ansi(bat_output)

                if self._current_preview_type != "bat":
                    self._current_preview_type = "none"
                    await self.remove_children()
                    self.remove_class("full", "clip")

                    await self.mount(
                        Static(new_content, id="text_preview", classes="inner_preview")
                    )
                    self.query_one(Static).can_focus = True
                    self.add_class("bar")
                    self._current_preview_type = "bat"
                else:
                    self.query_one("#text_preview", Static).update(new_content)

                self.border_title = titles.bat
                self.remove_class("full", "clip")
                if preview_full:
                    self.add_class("full")
                else:
                    self.add_class("clip")
                return True
            else:
                error_message = stderr.decode("utf-8", errors="ignore")
                self._current_preview_type = "none"
                await self.remove_children()
                self.notify(
                    error_message,
                    title="Plugins: Bat",
                    severity="warning",
                )
                return False
        except (FileNotFoundError, Exception) as e:
            self.notify(str(e), title="Plugins: Bat", severity="warning")
            return False

    async def _show_normal_file_preview(self) -> None:
        """Render file preview using TextArea, updating in place if possible."""
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

        is_special_content = self._current_content in (
            config["interface"]["preview_binary"],
            config["interface"]["preview_error"],
        )
        language = (
            "markdown"
            if is_special_content
            else EXT_TO_LANG_MAP.get(
                path.splitext(self._current_file_path)[1], "markdown"
            )
        )

        if self._current_preview_type != "normal_text":
            self._current_preview_type = "none"
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

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
            self._current_preview_type = "normal_text"
        else:
            text_area = self.query_one("#text_preview", CustomTextArea)
            text_area.text = text_to_display
            text_area.language = language

        self.border_title = titles.file

    async def _render_preview(self) -> None:
        """Render function dispatcher."""
        if self._current_file_path is None:
            pass
        elif self._is_image:
            await self._show_image_preview()
        elif self._is_archive:
            await self._show_archive_preview()
        elif self._current_content is None:
            pass
        else:
            # you wouldn't want to re-render a failed thing, would you?
            is_special_content = self._current_content in (
                config["interface"]["preview_binary"],
                config["interface"]["preview_error"],
            )
            if (
                config["plugins"]["bat"]["enabled"]
                and not is_special_content
                and await self._show_bat_file_preview()
            ):
                self.log("bat success")
            else:
                await self._show_normal_file_preview()

    async def _show_folder_preview(self, folder_path: str) -> None:
        """
        Show the folder in the preview container.
        Args:
            folder_path(str): The folder path
        """
        if self._current_preview_type != "folder":
            self._current_preview_type = "none"
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

            await self.mount(
                FileList(
                    id="folder_preview",
                    name=folder_path,
                    classes="file-list inner_preview",
                    dummy=True,
                    enter_into=folder_path,
                )
            )
            self._current_preview_type = "folder"

        folder_preview = self.query_one("#folder_preview")
        folder_preview.dummy_update_file_list(
            cwd=folder_path,
        )
        self.border_title = titles.folder

    async def _show_archive_preview(self) -> None:
        """Render archive preview, updating in place if possible."""
        if self._current_preview_type != "archive":
            self._current_preview_type = "none"
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

            # Use normal FileList instead of ArchiveFileList
            await self.mount(
                FileList(
                    id="archive_preview",
                    classes="file-list inner_preview",
                    dummy=True,
                )
            )
            self._current_preview_type = "archive"

        self.query_one("#archive_preview", FileList).create_archive_list(
            self._current_content
        )
        self.border_title = titles.archive

    def any_in_queue(self) -> bool:
        if self._queued_task is not None:
            self._queued_task(self._queued_task_args)
            self._queued_task, self._queued_task_args = None, None
            return True
        return False

    def show_preview(self, file_path: str) -> None:
        """
        Debounce requests, then show preview
        Args:
            file_path(str): The file path
        """
        if (
            any(
                worker.is_running
                and worker.node is self
                and worker.name == "_perform_show_preview"
                for worker in self.app.workers
            )
            # toggle hide
            or "hide" in self.classes
            # horizontal breakpoints
            or "-nopreview" in self.screen.classes
            or "-filelistonly" in self.screen.classes
        ):
            self._queued_task = self._perform_show_preview
            self._queued_task_args = file_path
        else:
            self._perform_show_preview(file_path)

    @work(thread=True)
    def _perform_show_preview(self, file_path: str) -> None:
        """
        Load file content in a worker and then render the preview.
        Args:
            file_path(str): The file path
        """
        if self.any_in_queue():
            return

        if path.isdir(file_path):
            self.app.call_from_thread(self._update_ui, file_path, is_dir=True)
        else:
            is_image = any(file_path.endswith(ext) for ext in PIL_EXTENSIONS)
            is_archive = any(file_path.endswith(ext) for ext in ARCHIVE_EXTENSIONS)
            content = None
            if is_archive:
                try:
                    with Archive(file_path, "r") as archive:
                        if config["settings"]["preview_full"]:
                            all_files = []
                            for member in archive.infolist():
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
                        else:
                            top_level_files = set()
                            top_level_dirs = set()
                            for member in archive.infolist():
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

                                filename = filename.replace("\\", "/")
                                if not filename:
                                    continue

                                parts = filename.strip("/").split("/")
                                if len(parts) == 1 and not is_dir:
                                    top_level_files.add(parts[0])
                                elif parts and parts[0]:
                                    top_level_dirs.add(parts[0])

                            top_level_files -= top_level_dirs
                            all_files = sorted([
                                d + "/" for d in top_level_dirs
                            ]) + sorted(list(top_level_files))
                    content = all_files
                except (
                    zipfile.BadZipFile,
                    tarfile.TarError,
                    ValueError,
                    FileNotFoundError,
                ):
                    content = [config["interface"]["preview_error"]]
            elif not is_image:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    content = config["interface"]["preview_binary"]
                except (FileNotFoundError, PermissionError, OSError, MemoryError):
                    # not taking my chances with a memory error
                    content = config["interface"]["preview_error"]

            if self.any_in_queue():
                return

            self.app.call_from_thread(
                self._update_ui,
                file_path,
                is_dir=False,
                is_image=is_image,
                is_archive=is_archive,
                content=content,
            )

        if self.any_in_queue():
            return
        else:
            self._queued_task = None

    async def _update_ui(
        self,
        file_path: str,
        is_dir: bool,
        is_image: bool = False,
        is_archive: bool = False,
        content: str | list[str] | None = None,
    ) -> None:
        """
        Update the preview UI. This runs on the main thread.
        """
        self._current_file_path = file_path
        if is_dir:
            self._is_image = False
            self._current_content = None
            await self._show_folder_preview(file_path)
        else:
            self._is_image = is_image
            self._is_archive = is_archive
            self._current_content = content
            await self._render_preview()

    async def on_resize(self, event: events.Resize) -> None:
        """Re-render the preview on resize if it's was rendered by batcat and height changed."""
        if (
            self._current_preview_type == "bat"
            and "clip" in self.classes
            and event.size.height != self._initial_height
        ) or self._current_preview_type == "normal_text":
            await self._render_preview()
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
        self.any_in_queue()
