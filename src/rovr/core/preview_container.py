import subprocess
from dataclasses import dataclass
from os import path
from typing import cast

import textual_image.widget as timg
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError
from PIL.Image import Image as PILImage
from rich.syntax import Syntax
from rich.text import Text
from rich.traceback import Traceback
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.highlight import guess_language
from textual.message import Message
from textual.widgets import Static

from rovr.classes.archive import Archive, BadArchiveError
from rovr.core import FileList
from rovr.functions.path import MimeResult, get_mime_type, match_mime_to_preview_type
from rovr.functions.utils import should_cancel
from rovr.variables.constants import PreviewContainerTitles, config, file_executable

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
        self._mime_type: MimeResult | None = None
        self._preview_texts: list[str] = config["interface"]["preview_text"].values()
        self.pdf = PDFHandler()
        # Debouncing mechanism
        self._queued_task = None
        self._queued_task_args: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(config["interface"]["preview_text"]["start"], classes="special")

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

    def any_in_queue(self) -> bool:
        """Check if there's a queued task and run it if so.

        Returns:
            bool: True if queue was processed or cancelled, False otherwise.
        """
        if should_cancel():
            return True
        if self._queued_task is not None:
            self._queued_task(self._queued_task_args)
            self._queued_task, self._queued_task_args = None, None
            return True
        return False

    def show_image_preview(self, depth: int = 0) -> None:
        """Show image preview. Runs in a thread."""
        self.app.call_from_thread(setattr, self, "border_title", titles.image)
        if should_cancel() or self._current_file_path is None:
            return

        try:
            pil_object: PILImage = Image.open(self._current_file_path)
        except UnidentifiedImageError:
            if should_cancel():
                return
            self.app.call_from_thread(self.remove_children)
            self.app.call_from_thread(
                self.mount,
                Static(
                    "Cannot render image (is the encoding wrong?)",
                    classes="special",
                ),
            )
            return
        except FileNotFoundError:
            if should_cancel():
                return
            self.app.call_from_thread(self.remove_children)
            self.app.call_from_thread(
                self.mount,
                Static(
                    config["interface"]["preview_text"]["error"],
                    classes="special",
                ),
            )
            return

        if not self.has_child(".image_preview"):
            self.app.call_from_thread(self.remove_children)
            self.app.call_from_thread(self.remove_class, "bat", "full", "clip")

            if should_cancel():
                return

            image_widget = timg.__dict__[
                config["interface"]["image_protocol"] + "Image"
            ](
                pil_object,
                classes="image_preview",
            )
            image_widget.can_focus = True
            self.app.call_from_thread(self.mount, image_widget)
        else:
            try:
                if should_cancel():
                    return
                image_widget = self.query_one(".image_preview")
                self.app.call_from_thread(setattr, image_widget, "image", pil_object)
            except NoMatches:
                if should_cancel() or depth >= 1:
                    return
                self.app.call_from_thread(self.remove_children)
                self.show_image_preview(depth=depth + 1)
                return

        if should_cancel():
            return

    def show_pdf_preview(self, depth: int = 0) -> None:
        """Show PDF preview. Runs in a thread.

        Raises:
            ValueError: If PDF conversion returns 0 pages.
        """
        self.app.call_from_thread(setattr, self, "border_title", titles.pdf)

        if should_cancel() or self._current_file_path is None:
            return

        # Convert PDF to images if not already done
        if self.pdf.images is None:
            poppler_folder: str | None = cast(
                str | None, config["plugins"]["poppler"]["poppler_folder"]
            )
            if poppler_folder == "":
                poppler_folder = None
            try:
                result = convert_from_path(
                    self._current_file_path,
                    transparent=False,
                    fmt="png",
                    single_file=False,
                    use_pdftocairo=config["plugins"]["poppler"]["use_pdftocairo"],
                    thread_count=config["plugins"]["poppler"]["threads"],
                    poppler_path=poppler_folder,  # type: ignore[arg-type]
                )
                if len(result) == 0:
                    raise ValueError(
                        "Obtained 0 pages from Poppler. Something may have gone wrong..."
                    )
            except Exception as exc:
                if should_cancel():
                    return
                self.app.call_from_thread(self.remove_children)
                self.app.call_from_thread(
                    self.mount,
                    Static(f"{type(exc).__name__}: {str(exc)}", classes="special"),
                )
                return

            self.pdf.images = result
            self.pdf.total_pages = len(self.pdf.images)
            self.pdf.current_page = 0

        if should_cancel():
            return

        current_image = self.pdf.images[self.pdf.current_page]

        self.app.call_from_thread(
            setattr,
            self,
            "border_subtitle",
            f"Page {self.pdf.current_page + 1}/{self.pdf.total_pages}",
        )

        if not self.has_child(".image_preview"):
            self.app.call_from_thread(self.remove_children)
            self.app.call_from_thread(self.remove_class, "bat", "full", "clip")

            if should_cancel():
                return

            image_widget = timg.__dict__[
                config["interface"]["image_protocol"] + "Image"
            ](
                current_image,
                classes="image_preview",
            )
            image_widget.can_focus = True
            self.app.call_from_thread(self.mount, image_widget)
        else:
            try:
                if should_cancel():
                    return
                image_widget = self.query_one(".image_preview")
                self.app.call_from_thread(setattr, image_widget, "image", current_image)
            except Exception:
                if should_cancel() or depth >= 1:
                    return
                self.app.call_from_thread(self.remove_children)
                self.show_pdf_preview(depth=depth + 1)

        if should_cancel():
            return

    def show_bat_file_preview(self) -> bool:
        """Show bat file preview. Runs in a thread.

        Returns:
            bool: True if successful, False otherwise.
        """
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
        command.extend(["--", self._current_file_path])

        if should_cancel():
            return False
        self.app.call_from_thread(setattr, self, "border_title", titles.bat)

        try:
            # Use synchronous subprocess since we're already in a thread
            result = subprocess.run(
                command,
                capture_output=True,
                text=False,
            )

            if should_cancel():
                return False

            if result.returncode == 0:
                bat_output = result.stdout.decode("utf-8", errors="ignore")
                new_content = Text.from_ansi(bat_output)

                if should_cancel():
                    return False

                if not self.has_child("Static"):
                    self.app.call_from_thread(self.remove_children)

                    if should_cancel():
                        return False

                    static_widget = Static(new_content, classes="bat_preview")
                    self.app.call_from_thread(self.mount, static_widget)
                    if should_cancel():
                        return False
                    static_widget.can_focus = True
                else:
                    static_widget: Static = self.query_one(Static)
                    self.app.call_from_thread(static_widget.update, new_content)
                    self.app.call_from_thread(static_widget.set_classes, "bat_preview")

                return True
            else:
                error_message = result.stderr.decode("utf-8", errors="ignore")
                if should_cancel():
                    return False
                self.app.call_from_thread(self.remove_children)
                self.app.call_from_thread(
                    self.notify,
                    error_message,
                    title="Plugins: Bat",
                    severity="warning",
                )
                return False
        except Exception as e:
            if should_cancel():
                return False
            self.app.call_from_thread(
                self.notify, str(e), title="Plugins: Bat", severity="error"
            )
            self.log(Traceback())
            return False

    def show_normal_file_preview(self) -> None:
        """Show normal file preview with syntax highlighting. Runs in a thread."""
        if should_cancel():
            return
        self.app.call_from_thread(setattr, self, "border_title", titles.file)

        if not isinstance(self._current_content, str):
            # force read by bruteforcing encoding methods
            encodings_to_try = [
                "utf8",
                "utf16",
                "utf32",
                "latin1",
                "iso8859-1",
                "mbcs",
                "ascii",
                "us-ascii",
            ]
            for encoding in encodings_to_try:
                try:
                    with open(self._current_file_path, "r", encoding=encoding) as f:
                        self._current_content = f.read(1024)
                    break
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
            if self._current_content is None:
                self._current_content = config["interface"]["preview_text"]["error"]
                self.mount_special_messages()
                return

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
        language = (
            guess_language(text_to_display, path=self._current_file_path) or "text"
        )
        syntax = Syntax(
            text_to_display,
            lexer=language,
            line_numbers=config["interface"]["show_line_numbers"],
            word_wrap=False,
            tab_size=4,
            theme=config["theme"]["preview"],
            background_color="default",
            code_width=max_width,
        )

        if should_cancel():
            return

        if not self.has_child("Static"):
            self.app.call_from_thread(self.remove_children)

            if should_cancel():
                return

            self.app.call_from_thread(self.mount, Static(syntax))
        else:
            static_widget = self.query_one(Static)
            self.app.call_from_thread(static_widget.update, syntax)

        if should_cancel():
            return

    def show_folder_preview(self, folder_path: str) -> None:
        """Show folder preview. Runs in a thread."""
        if should_cancel():
            return
        self.app.call_from_thread(setattr, self, "border_title", titles.folder)

        if not self.has_child("FileList"):
            self.app.call_from_thread(self.remove_children)

            if should_cancel():
                return

            self.app.call_from_thread(
                self.mount,
                FileList(
                    name=folder_path,
                    classes="file-list",
                    dummy=True,
                    enter_into=folder_path,
                ),
            )

        if should_cancel():
            return

        this_list: FileList = self.query_one(FileList)
        main_list: FileList = self.app.query_one("#file_list", FileList)
        this_list.sort_by = main_list.sort_by
        this_list.sort_descending = main_list.sort_descending

        # Schedule the update as a separate thread
        this_list.dummy_update_file_list(cwd=folder_path)

        self.app.call_from_thread(this_list.set_classes, "file-list")

        if should_cancel():
            return

    def show_archive_preview(self) -> None:
        """Show archive preview. Runs in a thread."""
        if should_cancel():
            return
        self.app.call_from_thread(setattr, self, "border_title", titles.archive)

        if not self.has_child("FileList"):
            self.app.call_from_thread(self.remove_children)

            if should_cancel():
                return

            self.app.call_from_thread(
                self.mount,
                FileList(
                    classes="archive-list",
                    dummy=True,
                ),
            )

        if should_cancel():
            return

        # Schedule the async update on the main thread
        self.query_one(FileList).create_archive_list(self._current_content)

        self.app.call_from_thread(self.query_one(FileList).set_classes, "archive-list")

        if should_cancel():
            return

    async def show_preview(self, file_path: str) -> None:
        """
        Public method to show preview. Uses debouncing pattern.
        """
        if (
            "hide" in self.classes
            or "-nopreview" in self.screen.classes
            or "-filelistonly" in self.screen.classes
        ):
            self._pending_preview_path = file_path
            return
        self._pending_preview_path = None

        # Debounce: check if worker is running
        if any(
            worker.is_running
            and worker.node is self
            and worker.name == "perform_show_preview"
            for worker in self.app.workers
        ):
            self._queued_task = self.perform_show_preview
            self._queued_task_args = file_path
        else:
            self.perform_show_preview(file_path)

    @work(exclusive=True, thread=True)
    def perform_show_preview(self, file_path: str) -> None:
        """Main preview worker. Runs in a thread."""
        try:
            if self.any_in_queue():
                return

            self.app.call_from_thread(setattr, self, "border_subtitle", "")
            if should_cancel():
                return
            self.post_message(self.SetLoading(True))

            # Reset PDF state when changing files
            if file_path != self._current_file_path:
                self.pdf.images = None
                self.pdf.current_page = 0
                self.pdf.total_pages = 0

            if path.isdir(file_path):
                self.update_ui(
                    file_path=file_path,
                    mime_type=MimeResult("basic", "inode/directory"),
                    file_type="folder",
                )
            else:
                content = None  # for now
                mime_result = get_mime_type(file_path)
                self.log(mime_result)
                if mime_result is None:
                    self.log(f"Could not get MIME type for {file_path}")
                    self.update_ui(
                        file_path=file_path,
                        file_type="file",
                        content=config["interface"]["preview_text"]["error"],
                    )
                    self.call_later(lambda: self.post_message(self.SetLoading(False)))
                    return
                content = mime_result.content

                file_type = match_mime_to_preview_type(mime_result.mime_type)
                if file_type is None:
                    self.log("Could not match MIME type to preview type")
                    self.update_ui(
                        file_path=file_path,
                        file_type="file",
                        mime_type=mime_result,
                        content=config["interface"]["preview_text"]["error"],
                    )
                    self.call_later(lambda: self.post_message(self.SetLoading(False)))
                    return
                elif file_type == "remime":
                    mime_result = get_mime_type(file_path, ["basic", "puremagic"])
                    if mime_result is None:
                        self.log("Could not get MIME type for remime")
                        self.update_ui(
                            file_path=file_path,
                            file_type="file",
                            content=config["interface"]["preview_text"]["error"],
                            mime_type=mime_result,
                        )
                        self.call_later(
                            lambda: self.post_message(self.SetLoading(False))
                        )
                        return
                    file_type = match_mime_to_preview_type(mime_result.mime_type)
                    if file_type is None:
                        self.log("Could not match MIME type to preview type")
                        self.update_ui(
                            file_path=file_path,
                            file_type="file",
                            mime_type=mime_result,
                            content=config["interface"]["preview_text"]["error"],
                        )
                        self.call_later(
                            lambda: self.post_message(self.SetLoading(False))
                        )
                        return
                self.log(f"Previewing as {file_type} (MIME: {mime_result.mime_type})")

                if file_type == "archive":
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
                        BadArchiveError,
                        ValueError,
                        FileNotFoundError,
                    ):
                        content = [config["interface"]["preview_text"]["error"]]

                self.update_ui(
                    file_path,
                    file_type=file_type,
                    content=content,
                    mime_type=mime_result,
                )

            if should_cancel():
                return
            self.call_later(lambda: self.post_message(self.SetLoading(False)))

            if self.any_in_queue():
                return
            else:
                self._queued_task = None
        except Exception as exc:
            from rich.traceback import Traceback

            self.log(Traceback.from_exception(type(exc), exc, exc.__traceback__))
            self.app.call_from_thread(
                self.notify,
                f"{type(exc).__name__} was raised while generating the preview",
            )

    def update_ui(
        self,
        file_path: str,
        file_type: str,
        content: str | list[str] | None = None,
        mime_type: MimeResult | None = None,
    ) -> None:
        """
        Update the preview UI. Runs in a thread, uses call_from_thread for UI ops.
        """
        self._current_file_path = file_path
        self._current_content = content
        self._mime_type = mime_type

        self._file_type = file_type
        self.app.call_from_thread(self.remove_class, "pdf")
        if file_type == "folder":
            self.log("Showing folder preview")
            self.show_folder_preview(file_path)
        elif file_type == "image":
            self.log("Showing image preview")
            self.show_image_preview()
        elif file_type == "archive":
            self.log("Showing archive preview")
            self.show_archive_preview()
        elif file_type == "pdf":
            self.log("Showing pdf preview")
            self.app.call_from_thread(self.add_class, "pdf")
            self.show_pdf_preview()
        else:
            if content in self._preview_texts:
                self.log("Showing special preview")
                self.mount_special_messages()
            else:
                if config["plugins"]["bat"]["enabled"]:
                    self.log("Showing bat preview")
                    if self.show_bat_file_preview():
                        return
                self.show_normal_file_preview()

    def mount_special_messages(self) -> None:
        """Mount special messages. Runs in a thread."""
        if should_cancel():
            return
        self.log(self._mime_type)
        assert isinstance(self._current_content, str)
        self.app.call_from_thread(setattr, self, "border_title", "")

        display_content: str = self._current_content
        if self._mime_type:
            display_content = f"MIME Type: {self._mime_type.mime_type}"
            if config["plugins"]["file_one"]["get_description"]:
                try:
                    process = subprocess.run(
                        [file_executable, "--brief", "--", self._current_file_path],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=1,
                    )
                    display_content += f"\n{process.stdout.strip()}"
                except (subprocess.SubprocessError, FileNotFoundError):
                    from rich.traceback import Traceback

                    self.log(Traceback())

        if self.has_child("Static"):
            static_widget: Static = self.query_one(Static)
            self.app.call_from_thread(static_widget.update, display_content)
            self.app.call_from_thread(static_widget.set_classes, "special")
        else:
            self.app.call_from_thread(self.remove_children)
            if should_cancel():
                return
            static_widget = Static(display_content, classes="special")
            self.app.call_from_thread(self.mount, static_widget)
        static_widget.can_focus = True
        if should_cancel():
            return

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Handle mouse scroll up for PDF navigation."""
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            if self.pdf.current_page > 0:
                self.pdf.current_page -= 1
                self._trigger_pdf_update()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Handle mouse scroll down for PDF navigation."""
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            if self.pdf.current_page < self.pdf.total_pages - 1:
                self.pdf.current_page += 1
                self._trigger_pdf_update()

    @work(thread=True)
    def _trigger_pdf_update(self) -> None:
        """Trigger PDF preview update from a thread."""
        self.show_pdf_preview()

    def on_resize(self, event: events.Resize) -> None:
        """Re-render the preview on resize"""
        if self.has_child("Static") and event.size.height != self._initial_height:
            if self._current_content is not None:
                is_special_content = self._current_content in self._preview_texts
                if not is_special_content:
                    self._trigger_resize_update()
            self._initial_height = event.size.height

    @work(thread=True)
    def _trigger_resize_update(self) -> None:
        """Trigger resize update from a thread."""
        if config["plugins"]["bat"]["enabled"] and self.show_bat_file_preview():
            return
        self.show_normal_file_preview()

    def on_key(self, event: events.Key) -> None:
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
            self._trigger_pdf_update()
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

    @on(events.Show)
    def when_become_visible(self, event: events.Show) -> None:
        if self._pending_preview_path is not None:
            pending = self._pending_preview_path
            self._pending_preview_path = None
            self.perform_show_preview(pending)
