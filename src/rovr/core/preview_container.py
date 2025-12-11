import asyncio
import asyncio.subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from os import path

import textual_image.widget as timg
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError
from PIL.Image import Image as PILImage
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.highlight import guess_language, highlight
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Static
from textual.worker import Worker, WorkerCancelled, WorkerError

from rovr.classes import Archive
from rovr.core import FileList
from rovr.functions.path import get_mime_type, match_mime_to_preview_type
from rovr.functions.utils import should_cancel
from rovr.variables.constants import PreviewContainerTitles, config, file_executable
from rovr.variables.maps import (
    ARCHIVE_EXTENSIONS_FULL,
    PIL_EXTENSIONS,
)

titles = PreviewContainerTitles()


@dataclass
class PDFHandler:
    current_page: int = 0
    total_pages: int = 0
    images: list[PILImage] | None = None


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
        self._mime_type: str | None = None
        self._preview_texts: list[str] = config["interface"]["preview_text"].values()
        self.pdf = PDFHandler()
        self.set_loading_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static(config["interface"]["preview_text"]["start"], classes="wrap")

    def on_preview_container_set_loading(self, event: SetLoading) -> None:
        if not event.to:
            if self.set_loading_timer is not None:
                self.set_loading_timer.stop()
            self.set_loading(False)
        else:
            if not self.loading:
                self.set_loading_timer = self.set_timer(
                    0.15, lambda: self.set_loading(event.to)
                )

    def set_loading(self, loading: bool) -> None:
        if loading and all(
            not worker.is_running
            and worker.node is self
            and worker.name == "perform_show_preview"
            for worker in self.app.workers
        ):
            return
        return super().set_loading(loading)

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
        self.border_title = titles.image
        if should_cancel():
            return

        try:
            worker: Worker = self.app.run_in_thread(Image.open, self._current_file_path)
            result: PILImage | Exception = await worker.wait()
            if isinstance(result, Exception):
                raise result
            else:
                pil_object: PILImage = result
        except WorkerError:
            return
        except UnidentifiedImageError:
            if should_cancel():
                return
            async with self.batch():
                await self.remove_children()
                await self.mount(
                    Static(
                        "Cannot render image (is the encoding wrong?)",
                        id="text_preview",
                    )
                )
            return
        except FileNotFoundError:
            if should_cancel():
                return
            async with self.batch():
                await self.remove_children()
                await self.mount(
                    Static(
                        config["interface"]["preview_text"]["error"],
                        id="text_preview",
                    )
                )
            return

        if not self.has_child("#image_preview"):
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

            if should_cancel():
                return

            image_widget = timg.__dict__[
                config["settings"]["image_protocol"] + "Image"
            ](
                pil_object,
                id="image_preview",
                classes="inner_preview",
            )
            image_widget.can_focus = True
            await self.mount(image_widget)
        else:
            try:
                if should_cancel():
                    return
                image_widget = self.query_one("#image_preview")
                image_widget.image = pil_object
            except NoMatches:
                if should_cancel():
                    return
                async with self.batch():
                    await self.remove_children()
                    await self.show_image_preview()
                return

        if should_cancel():
            return

    async def show_pdf_preview(self) -> None:
        self.border_title = titles.pdf

        if should_cancel():
            return

        # Convert PDF to images if not already done
        if self.pdf.images is None:
            try:
                worker: Worker = self.app.run_in_thread(
                    convert_from_path,
                    str(self._current_file_path),
                    transparent=False,
                    fmt="png",
                    single_file=False,
                    use_pdftocairo=config["plugins"]["poppler"]["use_pdftocairo"],
                    thread_count=config["plugins"]["poppler"]["threads"],
                    poppler_path=config["plugins"]["poppler"]["poppler_folder"] or None,
                )
                result = await worker.wait()
                if isinstance(result, Exception):
                    raise result
                elif len(result) == 0:
                    raise ValueError(
                        "Obtained 0 pages from Poppler. Something may have gone wrong..."
                    )
            except Exception as exc:
                if should_cancel():
                    return
                await self.remove_children()
                await self.mount(
                    Static(
                        f"{type(exc).__name__}: {str(exc)}",
                        id="text_preview",
                    )
                )
                return

            self.pdf.images = result
            self.pdf.total_pages = len(self.pdf.images)
            self.pdf.current_page = 0

        if should_cancel():
            return

        current_image = self.pdf.images[self.pdf.current_page]

        self.border_subtitle = (
            f"Page {self.pdf.current_page + 1}/{self.pdf.total_pages}"
        )

        if not self.has_child("#image_preview"):
            await self.remove_children()
            self.remove_class("bat", "full", "clip")

            if should_cancel():
                return

            image_widget = timg.__dict__[
                config["settings"]["image_protocol"] + "Image"
            ](
                current_image,
                id="image_preview",
                classes="inner_preview",
            )
            image_widget.can_focus = True
            await self.mount(image_widget)
        else:
            try:
                if should_cancel():
                    return
                image_widget = self.query_one("#image_preview")
                image_widget.image = current_image
            except Exception:
                if should_cancel():
                    return
                await self.remove_children()
                await self.show_pdf_preview()

        if should_cancel():
            return

    async def show_bat_file_preview(self) -> bool:
        self.border_title = titles.bat
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

        if should_cancel():
            return False

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if should_cancel():
                return False

            if process.returncode == 0:
                bat_output = stdout.decode("utf-8", errors="ignore")
                new_content = Text.from_ansi(bat_output)

                if should_cancel():
                    return False

                if not self.has_child("Static"):
                    await self.remove_children()

                    if should_cancel():
                        return False

                    static_widget = Static(
                        new_content, id="text_preview", classes="inner_preview"
                    )
                    await self.mount(static_widget)
                    if should_cancel():
                        return False
                    static_widget.can_focus = True
                else:
                    static_widget: Static = self.query_one(Static)
                    static_widget.update(new_content)
                static_widget.classes = ""

                return not should_cancel()
            else:
                error_message = stderr.decode("utf-8", errors="ignore")
                if should_cancel():
                    return False
                await self.remove_children()
                self.notify(
                    error_message,
                    title="Plugins: Bat",
                    severity="warning",
                )
                return False
        except Exception as e:
            if should_cancel():
                return False
            self.notify(str(e), title="Plugins: Bat", severity="warning")
            return False

    async def show_normal_file_preview(self) -> None:
        if should_cancel():
            return
        self.border_title = titles.file

        assert isinstance(self._current_content, str)

        lines = self._current_content.splitlines()
        max_lines = self.size.height
        if max_lines > 0:
            if len(lines) > max_lines:
                lines = lines[:max_lines]
        else:
            lines = []
        max_width = self.size.width * 2
        if max_width > 0:
            processed_lines = []
            for line in lines:
                if len(line) > max_width:
                    processed_lines.append(line[:max_width])
                else:
                    processed_lines.append(line)
            lines = processed_lines
        text_to_display = "\n".join(lines)
        # add syntax highlighting
        text_to_display = highlight(
            text_to_display,
            language=guess_language(text_to_display, path=self._current_file_path),
            tab_size=4,
        )

        if should_cancel():
            return

        if should_cancel():
            return

        if not self.has_child("Static"):
            await self.remove_children()

            if should_cancel():
                return

            await self.mount(
                Static(
                    text_to_display,
                    id="text_preview",
                )
            )
        else:
            self.query_one(Static).update(text_to_display)

        if should_cancel():
            return

    async def show_folder_preview(self, folder_path: str) -> None:
        self.border_title = titles.folder
        if should_cancel():
            return

        if not self.has_child("FileList"):
            await self.remove_children()

            if should_cancel():
                return

            await self.mount(
                FileList(
                    name=folder_path,
                    classes="file-list inner_preview",
                    dummy=True,
                    enter_into=folder_path,
                )
            )

        if should_cancel():
            return

        this_list: FileList = self.query_one(FileList)
        main_list: FileList = self.app.query_one("#file_list", FileList)
        this_list.sort_by = main_list.sort_by
        this_list.sort_descending = main_list.sort_descending

        updater_worker: Worker = this_list.dummy_update_file_list(
            cwd=folder_path,
        )

        try:
            await updater_worker.wait()
        except WorkerCancelled:
            return

        if should_cancel():
            return

    async def show_archive_preview(self) -> None:
        self.border_title = titles.archive
        if should_cancel():
            return

        if not self.has_child("FileList"):
            await self.remove_children()

            if should_cancel():
                return

            await self.mount(
                FileList(
                    classes="file-list inner_preview",
                    dummy=True,
                )
            )

        if should_cancel():
            return

        updater_worker: Worker = self.query_one(FileList).create_archive_list(
            self._current_content
        )

        try:
            await updater_worker.wait()
        except WorkerCancelled:
            return

        if should_cancel():
            return

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

    @work(exclusive=True, thread=True, exit_on_error=False)
    def perform_show_preview(self, file_path: str) -> None:
        self.border_subtitle = ""
        if should_cancel():
            return
        self.post_message(self.SetLoading(True))

        # Reset PDF state when changing files
        if file_path != self._current_file_path:
            self.pdf.images = None
            self.pdf.current_page = 0
            self.pdf.total_pages = 0

        mime_type: str | None = None

        if path.isdir(file_path):
            self.app.call_from_thread(
                self.update_ui, file_path=file_path, file_type="folder"
            )
        else:
            file_type: str | None = None

            if config["plugins"]["file_one"]["enabled"] and file_executable is not None:
                if should_cancel():
                    return
                mime_type = self.app.call_from_thread(get_mime_type, file_path)
                if mime_type is not None:
                    file_type = match_mime_to_preview_type(
                        mime_type,
                        config["plugins"]["file_one"]["mime_rules"],
                    )
                    if (
                        file_type == "pdf"
                        and not config["plugins"]["poppler"]["enabled"]
                    ):
                        file_type = "file"

            if file_type is None:
                lower_file_path = file_path.lower()
                if (
                    lower_file_path.endswith(".pdf")
                    and config["plugins"]["poppler"]["enabled"]
                ):
                    file_type = "pdf"
                elif any(lower_file_path.endswith(ext) for ext in PIL_EXTENSIONS):
                    file_type = "image"
                elif any(
                    lower_file_path.endswith(ext) for ext in ARCHIVE_EXTENSIONS_FULL
                ):
                    file_type = "archive"
                else:
                    file_type = "file"

            content = None

            if should_cancel():
                return

            match file_type:
                case "archive":
                    try:
                        with Archive(file_path, "r") as archive:
                            all_files = []
                            for member in archive.infolist():
                                if should_cancel():
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
                case "image" | "pdf":
                    pass
                case _:
                    if should_cancel():
                        return
                    # prevent files > 1mb from being
                    # read because are you stupid, why
                    # would you use rovr for that anyways
                    try:
                        size = path.getsize(file_path)
                        if size > 1024**2:
                            content = config["interface"]["preview_text"]["too_large"]
                        elif size == 0:
                            content = config["interface"]["preview_text"]["empty"]
                        else:
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                            except UnicodeDecodeError:
                                content = config["interface"]["preview_text"]["binary"]
                            except (
                                FileNotFoundError,
                                PermissionError,
                                OSError,
                                MemoryError,
                            ):
                                content = config["interface"]["preview_text"]["error"]
                    except FileNotFoundError:
                        content = config["interface"]["preview_text"]["error"]
                        if path.exists(file_path):
                            raise Exception from None
            if should_cancel():
                return

            self.app.call_from_thread(
                self.update_ui,
                file_path,
                file_type=file_type,
                content=content,
                mime_type=mime_type,
            )

        self.call_after_refresh(lambda: self.post_message(self.SetLoading(False)))

    async def update_ui(
        self,
        file_path: str,
        file_type: str,
        content: str | list[str] | None = None,
        mime_type: str | None = None,
    ) -> None:
        """
        Update the preview UI. This runs on the main thread.
        """
        self._current_file_path = file_path
        self._current_content = content
        self._mime_type = mime_type

        self._file_type = file_type
        self.remove_class("pdf")

        if file_type == "folder":
            await self.show_folder_preview(file_path)
        elif file_type == "image":
            await self.show_image_preview()
        elif file_type == "archive":
            await self.show_archive_preview()
        elif file_type == "pdf":
            self.add_class("pdf")
            await self.show_pdf_preview()
        elif content is not None:
            if content in self._preview_texts:
                await self.mount_special_messages()
            else:
                if not (
                    config["plugins"]["bat"]["enabled"]
                    and await self.show_bat_file_preview()
                ):
                    await self.show_normal_file_preview()

    async def mount_special_messages(self) -> None:
        self.border_title = ""
        if should_cancel():
            return

        assert isinstance(self._current_content, str)

        display_content: str = self._current_content
        if (
            self._current_content == config["interface"]["preview_text"]["binary"]
            and self._mime_type is not None
        ):
            display_content = (
                f"{self._current_content}\n\n[dim]MIME type: {self._mime_type}[/]"
            )

        if self.has_child("Static"):
            static_widget: Static = self.query_one(Static)
            static_widget.update(display_content)
        else:
            await self.remove_children()
            if should_cancel():
                return
            static_widget = Static(display_content)
            await self.mount(static_widget)
        static_widget.can_focus = True
        static_widget.classes = "special"
        if should_cancel():
            return

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        # pdf for now, text later on
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            if self.pdf.current_page > 0:
                self.pdf.current_page -= 1
                await self.show_pdf_preview()

    async def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        # pdf for now, text later on
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            if self.pdf.current_page < self.pdf.total_pages - 1:
                self.pdf.current_page += 1
                await self.show_pdf_preview()

    async def on_resize(self, event: events.Resize) -> None:
        """Re-render the preview on resize"""
        if self.has_child("Static") and event.size.height != self._initial_height:
            if self._current_content is not None:
                is_special_content = self._current_content in self._preview_texts
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
        from rovr.functions.utils import check_key

        # Handle PDF page navigation
        if (
            self.border_title == titles.pdf
            and self._file_type == "pdf"
            and self.pdf.images is not None
        ):
            if (
                check_key(
                    event, config["keybinds"]["down"] + config["keybinds"]["page_down"]
                )
                and self.pdf.current_page < self.pdf.total_pages - 1
            ):
                event.stop()
                self.pdf.current_page += 1
            elif (
                check_key(
                    event, config["keybinds"]["up"] + config["keybinds"]["page_up"]
                )
                and self.pdf.current_page > 0
            ):
                event.stop()
                self.pdf.current_page -= 1
            elif check_key(event, config["keybinds"]["home"]):
                event.stop()
                self.pdf.current_page = 0
            elif check_key(event, config["keybinds"]["end"]):
                event.stop()
                self.pdf.current_page = self.pdf.total_pages - 1
            else:
                return
            await self.show_pdf_preview()
        elif self.border_title == titles.archive:
            widget: FileList = self.query_one(FileList)
            if check_key(event, config["keybinds"]["up"]):
                event.stop()
                widget.scroll_up(animate=False)
            elif check_key(event, config["keybinds"]["down"]):
                event.stop()
                widget.scroll_down(animate=False)
            elif check_key(event, config["keybinds"]["page_up"]):
                event.stop()
                widget.scroll_page_up(animate=False)
            elif check_key(event, config["keybinds"]["page_down"]):
                event.stop()
                widget.scroll_page_down(animate=False)
            elif check_key(event, config["keybinds"]["home"]):
                event.stop()
                widget.scroll_home(animate=False)
            elif check_key(event, config["keybinds"]["end"]):
                event.stop()
                widget.scroll_end(animate=False)
            # elif check_key(event, config["keybinds"]["preview_scroll_left"]):
            #     event.stop()
            #     widget.scroll_left(animate=False)
            # elif check_key(event, config["keybinds"]["preview_scroll_right"]):
            #     event.stop()
            #     widget.scroll_right(animate=False)

    @on(events.Show)
    def when_become_visible(self, event: events.Show) -> None:
        if self._pending_preview_path is not None:
            pending = self._pending_preview_path
            self._pending_preview_path = None
            self.perform_show_preview(pending)
