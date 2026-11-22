from __future__ import annotations

import contextlib
import os
import subprocess
from dataclasses import dataclass, field
from functools import partial
from io import BytesIO
from os import path
from shutil import which
from typing import TYPE_CHECKING, Literal, cast

from PIL import Image
from PIL.Image import Image as PILImage
from rich.text import Text
from textual import work
from textual.widgets import Static

from rovr.classes.type_aliases import CacheSource
from rovr.components.text_preview import (
    LazyTextLines,
    WindowedTextPreview,
)
from rovr.functions import cache, icons, preview_utils, utils
from rovr.functions.ansi import ansi_to_rich_text
from rovr.functions.path import dump_exc
from rovr.variables.constants import (
    BAT_PREVIEW_CACHE_VERSION,
    BAT_PREVIEW_PAGE_SIZE,
    BAT_PREVIEWER_GROUP,
    PREVIEWER_GROUP,
    VIDEO_FPS,
    VIDEO_SCALE_FILTER,
    config,
    ffconf,
    titles,
)

if TYPE_CHECKING:
    from rovr.core.preview_container import PreviewContainer
else:
    PreviewContainer = object


@dataclass
class PDFHandler:
    # It is 0 indexed, although most poppler functions
    # like get_pdf_images expects 1 based indexing
    current_page: int = 0
    total_pages: int = 0
    images: list[PILImage] | None = None
    cairo_or_ppm = "cairo" if config["plugins"]["poppler"]["use_pdftocairo"] else "ppm"
    pdf_batch_size = config["plugins"]["poppler"]["pdf_batch_size"]

    def count_loaded(self) -> int:
        return 0 if self.images is None else len(self.images)

    def must_load_next_batch(self) -> bool:
        return self.current_page >= self.count_loaded()

    def should_load_next_batch(self) -> bool:
        if self.count_loaded() >= self.total_pages:
            return False

        # If going further down half the batch will cross currently loaded pages
        # then its better to preload in advance
        return (self.current_page + PDFHandler.pdf_batch_size // 2) >= self.count_loaded()

    def get_last_page_to_load(self) -> int:
        # We should load till current page, if user scrolls too fast and reaches
        # beyond the batch before our load. This can happen on slow loads, and smaller batch sizes
        last_page = max(
            self.current_page + 1,
            self.count_loaded() + PDFHandler.pdf_batch_size,
        )
        return min(last_page, self.total_pages)

    @staticmethod
    def get_poppler_folder() -> str | None:
        poppler_folder: str | None = config["plugins"]["poppler"]["poppler_folder"]
        if poppler_folder == "" or poppler_folder.lower() == "path":
            poppler_folder = None
        return poppler_folder


class PDFMixin:
    def update_current_pdf_page_by_diff(self: PreviewContainer, diff: int) -> None:
        """Updates the current pages by a diff"""
        self.update_current_pdf_page(self.pdf.current_page + diff)

    # Note : We must ensure that any update to current_page happens via this
    def update_current_pdf_page(self: PreviewContainer, current_page: int) -> None:
        """Updates the current pages and ensure to spawn a worker that will eventually load them"""
        if current_page < 0 or current_page >= self.pdf.total_pages:
            return
        if current_page == self.pdf.current_page:
            return

        self.pdf.current_page = current_page
        self.set_border(
            "subtitle",
            f"Page {self.pdf.current_page + 1}/{self.pdf.total_pages}",
        )
        self.run_worker(
            partial(self._show_pdf_preview, self._active_preview_token),
            thread=True,
            exclusive=True,
            group=PREVIEWER_GROUP,
        )

    def _show_pdf_preview(self: PreviewContainer, token: object) -> None:
        context_token = self.preview_token.set(token)
        try:
            self.show_pdf_preview()
        except utils.ExitNow:
            pass
        finally:
            self.preview_token.reset(context_token)

    def load_pdf_pages(
        self: PreviewContainer, first_page: int, last_page: int
    ) -> list[PILImage]:
        """
        Returns:
            List of images, one per pages fetched

        Raises:
            ValueError: If PDF conversion returns 0 pages.
            ExitNow: If this preview request is no longer active.
        """
        if first_page > last_page:
            raise ValueError(
                f"Invalid args, first_page={first_page} > last_page={last_page}"
            )

        from rovr.functions.pdf import get_pdf_images

        if self._current_file_path is None:
            raise utils.ExitNow()

        realpath = path.realpath(self._current_file_path)
        stat_res = os.stat(realpath)
        cached = [
            cache._load_image(
                realpath,
                "pdf",
                stat_res,
                self.IMAGE_CACHE_SIGNATURE,
                extra=str(page) + (self.pdf.cairo_or_ppm),
            )
            for page in range(first_page, last_page + 1)
        ]
        if all(image is not None for image in cached):
            return cast(list[PILImage], cached)

        result = get_pdf_images(
            str(realpath),
            first_page=first_page,
            last_page=last_page,
            use_pdftocairo=config["plugins"]["poppler"]["use_pdftocairo"],
            thread_count=config["plugins"]["poppler"]["threads"],
            poppler_path=PDFHandler.get_poppler_folder(),
        )
        if len(result) == 0:
            raise ValueError(
                "Obtained 0 pages from Poppler. Something may have gone wrong..."
            )
        # Resample images once when loaded for better performance
        if self.app.MULTIPROCESSING_PROCESS_ALLOWED:
            try:
                result = preview_utils.resample_batch(result)
            except ValueError as exc:
                if utils.multiprocessing_process_error_checker(self.app, exc):
                    result = preview_utils.resample_batch_sync(result)
                else:
                    raise
        else:
            result = preview_utils.resample_batch_sync(result)
        for page, image in zip(range(first_page, last_page + 1), result):
            cache._save_image(
                realpath,
                "pdf",
                stat_res,
                image,
                self.IMAGE_CACHE_SIGNATURE,
                extra=str(page) + (self.pdf.cairo_or_ppm),
            )
        return result

    def show_pdf_preview(
        self: PreviewContainer,
        title: bool = True,
        cache_source: CacheSource | None = None,
    ) -> None:
        """
        Show PDF preview. Runs in a thread.
        The job of this function is to load the pdf file for the first time.
        Or ensure the batched loading

        Raises:
            ExitNow: If this preview request is no longer active.
        """
        if utils.check_cancel() or self._current_file_path is None:
            return
        if title:
            self.set_border("title", titles.pdf)

        from rovr.functions.pdf import get_pdf_info

        # Convert PDF to images if not already done
        if self.pdf.images is None:
            try:
                realpath, stat_res, sig = cache_source or (
                    path.realpath(self._current_file_path),
                    os.stat(self._current_file_path),
                    (self.pdf.cairo_or_ppm, ""),
                )
                pdf_info: dict[str, str | int] | None = cache.load(
                    realpath,
                    "pdf_info",
                    stat_res,
                    sig,
                    pass_as=dict,
                )
                if pdf_info is None:
                    pdf_info = get_pdf_info(
                        self._current_file_path,
                        poppler_path=PDFHandler.get_poppler_folder(),
                    )
                    cache.save(
                        realpath,
                        "pdf_info",
                        stat_res,
                        sig,
                        data=pdf_info,
                    )
                self.pdf.total_pages = int(pdf_info.get("Pages", 0))

                result = self.load_pdf_pages(
                    first_page=1, last_page=self.pdf.get_last_page_to_load()
                )
            except utils.ExitNow:
                raise
            except Exception as exc:
                utils.check_cancel()
                self.call_from_thread(self.remove_children)
                self.call_from_thread(
                    self.mount,
                    Static(f"{type(exc).__name__}: {str(exc)}", classes="special"),
                )
                return
            self.pdf.images = result

            # The only one case when current page and border subtitles
            # should be manually adjusted. Not the best design though.
            self.pdf.current_page = 0
            self.set_border(
                "subtitle", f"Page {self.pdf.current_page + 1}/{self.pdf.total_pages}"
            )

        elif self.pdf.should_load_next_batch():
            # Saving the value per thread instead of recalculating after the load
            # Even if something changes in between, we want the threads that set the status to
            # loading, to always unset it

            try:
                result = self.load_pdf_pages(
                    first_page=self.pdf.count_loaded() + 1,
                    last_page=self.pdf.get_last_page_to_load(),
                )
            except Exception as exc:
                utils.check_cancel()
                self.call_from_thread(self.remove_children)
                self.call_from_thread(
                    self.mount,
                    Static(f"{type(exc).__name__}: {str(exc)}", classes="special"),
                )
                return
            # Note - This check_cancel() must be kept here, not before the `load_pdf_pages` call
            # That, somehow doesn't prevents multiple threads executing the load
            # even though, we successful prevent multiple threads
            # appending the results via this one
            # We don't want threads to Set the screen in Loading state, and never turn it back
            utils.check_cancel()

            # This mutation on the `images` object should be done by one one thread
            # and the entire flow of checking `should_load_next_batch` to loading
            # to appending the pages should be atomic.
            # At this point, we are using `check_cancel()` to allow only one thread
            # to reach here
            self.pdf.images += result

        utils.check_cancel()

        current_image = self.pdf.images[self.pdf.current_page]

        if image_widget := self.get_child(".image_preview"):
            utils.check_cancel()
            self.call_from_thread(setattr, image_widget, "image", current_image)
        else:
            self.call_from_thread(self.remove_children)
            self.call_from_thread(self.remove_class, "bat", "full", "clip")

            utils.check_cancel()

            image_widget = self.NewImage(current_image)
            image_widget.can_focus = True
            self.call_from_thread(self.mount, image_widget)

        utils.check_cancel()


class BatMixin:
    @staticmethod
    def _split_bat_page(content: Text) -> list[Text]:
        lines = list(content.split("\n", allow_blank=True))
        if lines and not lines[-1].plain:
            lines.pop()
        return lines

    def _get_bat_page(
        self: PreviewContainer,
        command: list[str],
        realpath: str,
        stat_res: os.stat_res,
        sig: tuple[str, str],
        page: int,
    ) -> list[Text]:
        start = page * BAT_PREVIEW_PAGE_SIZE + 1
        end = start + BAT_PREVIEW_PAGE_SIZE - 1
        cache_range = f"{start}:{end}"
        content = cache._load_text(realpath, "bat-page", stat_res, sig, cache_range)
        if content is None:
            process = subprocess.run(
                [*command, f"--line-range={cache_range}", "--", realpath],
                capture_output=True,
                timeout=5,
            )
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    process.args,
                    process.stdout,
                    process.stderr,
                )
            content = ansi_to_rich_text(process.stdout.decode("utf-8", errors="ignore"))
            cache._save_text(
                realpath,
                "bat-page",
                stat_res,
                sig,
                content,
                cache_range,
            )
        return self._split_bat_page(content)

    def _load_bat_page(
        self: PreviewContainer,
        token: object,
        text_preview: WindowedTextPreview,
        source: LazyTextLines,
        command: list[str],
        realpath: str,
        stat_res: os.stat_res,
        sig: tuple[str, str],
        page: int,
    ) -> None:
        context_token = self.preview_token.set(token)
        try:
            if token is not self._active_preview_token:
                return
            lines = self._get_bat_page(command, realpath, stat_res, sig, page)
            self.call_from_thread(text_preview.set_lazy_page, source, page, lines)
        except utils.ExitNow:
            return
        except subprocess.SubprocessError as exc:
            self.call_from_thread(
                text_preview.set_lazy_page,
                source,
                page,
                [Text(f"bat: {exc}", style="red")]
                + [Text()] * (BAT_PREVIEW_PAGE_SIZE - 1),
            )
        finally:
            self.preview_token.reset(context_token)

    def _count_bat_lines(
        self: PreviewContainer,
        token: object,
        text_preview: WindowedTextPreview,
        source: LazyTextLines,
        realpath: str,
        stat_res: os.stat_res,
        sig: tuple[str, str],
    ) -> None:
        context_token = self.preview_token.set(token)
        try:
            if token is not self._active_preview_token:
                return
            cached_line_count = cache.load(
                realpath, "bat-lines", stat_res, sig, pass_as=str
            )
            if cached_line_count is None:
                line_count = 0
                with open(realpath, "rb") as file:
                    for line_count, _ in enumerate(file, 1):
                        if (
                            line_count % 8192 == 0
                            and token is not self._active_preview_token
                        ):
                            return
                if token is not self._active_preview_token:
                    return
                cache.save(realpath, "bat-lines", stat_res, sig, str(line_count))
            else:
                line_count = int(cached_line_count)
            if token is not self._active_preview_token:
                return
            self.call_from_thread(text_preview.set_lazy_line_count, source, line_count)
        except (utils.ExitNow, OSError, ValueError):
            return
        finally:
            self.preview_token.reset(context_token)

    def show_bat_file_preview(self: PreviewContainer) -> bool:
        """Show bat file preview. Runs in a thread.

        Returns:
            bool: True if successful, False otherwise.

        Raises:
            ExitNow: If this preview request is no longer active.
        """
        from shutil import which

        # luckily shutil.which handles absolute path for us, thanks
        if not which(bat_executable := config["plugins"]["bat"]["executable"]):
            config["plugins"]["bat"]["enabled"] = False
            self.notify(
                f"Bat executable not found: {bat_executable}.\nDisabling bat plugin.",
                title="Plugins: Bat",
                severity="warning",
                markup=False,
            )
            return False

        command = [
            bat_executable,
            "--force-colorization",
            "--paging=never",
            "--wrap=never",
            "--style=numbers"
            if config["interface"]["show_line_numbers"]
            else "--style=plain",
        ]
        if self._current_file_path is None:
            raise utils.ExitNow()

        realpath = path.realpath(self._current_file_path)
        stat_res = os.stat(realpath)
        sig = (
            f"{BAT_PREVIEW_CACHE_VERSION}:{config['interface']['show_line_numbers']}",
            bat_executable,
        )

        if utils.should_cancel():
            return False

        self.set_border("title", titles.bat)

        try:
            first_page = self._get_bat_page(command, realpath, stat_res, sig, 0)

            if utils.should_cancel():
                return False

            token = self._active_preview_token
            text_preview: WindowedTextPreview

            def request_page(page: int) -> None:
                self.run_worker(
                    partial(
                        self._load_bat_page,
                        token,
                        text_preview,
                        source,
                        command,
                        realpath,
                        stat_res,
                        sig,
                        page,
                    ),
                    thread=True,
                    group=BAT_PREVIEWER_GROUP,
                )

            first_page_is_complete = len(first_page) < BAT_PREVIEW_PAGE_SIZE
            source = LazyTextLines(
                len(first_page) if first_page_is_complete else BAT_PREVIEW_PAGE_SIZE,
                BAT_PREVIEW_PAGE_SIZE,
                request_page,
            )
            source.set_page(0, first_page)
            existing_preview = self.get_child(WindowedTextPreview)
            if isinstance(existing_preview, WindowedTextPreview):
                text_preview = existing_preview
                self.call_from_thread(
                    text_preview.update_preview,
                    source,
                    language=None,
                    line_numbers=False,
                )
                self.call_from_thread(
                    text_preview.set_classes, "text_preview bat_preview"
                )
            else:
                self.call_from_thread(self.remove_children)

                if utils.should_cancel():
                    return False

                text_preview = self.call_from_thread(
                    lambda: WindowedTextPreview(
                        source, classes="text_preview bat_preview"
                    ).data_bind(type(self.app).ansi_color)
                )
                self.call_from_thread(self.mount, text_preview)
                if utils.should_cancel():
                    return False
            if not first_page_is_complete:
                self.run_worker(
                    partial(
                        self._count_bat_lines,
                        token,
                        text_preview,
                        source,
                        realpath,
                        stat_res,
                        sig,
                    ),
                    thread=True,
                    group=BAT_PREVIEWER_GROUP,
                )
            return True
        except subprocess.CalledProcessError as exc:
            if utils.should_cancel():
                return False
            self.notify(
                exc.stderr.decode("utf-8", errors="ignore"),
                title="Plugins: Bat",
                severity="warning",
                markup=False,
            )
            return False
        except utils.ExitNow:
            raise
        except Exception as exc:
            if utils.should_cancel():
                return False
            self.notify(
                str(exc),
                title="Plugins: Bat",
                severity="error",
                markup=False,
            )
            dump_exc(self, exc)
            return False


ffmpeg = ffconf["ffmpeg_path"]
ffprobe = ffconf["ffprobe_path"]
can_ffmpeg = ffconf["enabled"]


@dataclass
class VideoHandler:
    file: str | None = None
    mtime: int | float | None = None
    position: float = 0.0
    duration: float | None = None
    size: tuple[int, int] | None = None
    process: subprocess.Popen[bytes] | None = None
    running: bool = False
    ended: bool = False
    token: object = field(default_factory=object)
    seeking: Literal["forward", "backward"] | None = None


class VideoMixin:
    @staticmethod
    def _probe_video_duration(source: str, stat_res: os.stat_result) -> float | None:
        realpath = path.realpath(source)
        sig = (ffprobe, "duration")
        cached = cache.load(realpath, "video-duration", stat_res, sig)
        if cached is not None:
            with contextlib.suppress(ValueError):
                duration = float(cached)
                if 0 < duration < float("inf"):
                    return duration
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration"]
                + ["-of", "default=noprint_wrappers=1:nokey=1", source],
                capture_output=True,
                timeout=3,
                check=True,
            )
            duration = float(result.stdout)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
        if 0 < duration < float("inf"):
            cache.save(realpath, "video-duration", stat_res, sig, str(duration))
            return duration
        return None

    def _update_video_subtitle(self: PreviewContainer) -> None:
        if self._file_type != "video":
            return
        if self.video.seeking:
            status = (
                icons.get_icon("general", "fast_forward")
                if self.video.seeking == "forward"
                else icons.get_icon("general", "fast_backward")
            )[0]
        else:
            status = (
                icons.get_icon("general", "ended")
                if self.video.ended
                else icons.get_icon("general", "playing")
                if self.video.running
                else icons.get_icon("general", "paused")
            )[0]
        subtitle = status
        if self.video.duration is not None:
            position = int(min(self.video.position, self.video.duration))
            duration = int(self.video.duration)
            subtitle += f" {position // 60:02}:{position % 60:02} / {duration // 60:02}:{duration % 60:02}"
        if self.border_subtitle != subtitle:
            self.border_subtitle = subtitle

    def _start_video(self: PreviewContainer) -> None:
        if (
            self._file_type != "video"
            or not self.has_focus_within
            or (self.video.running or self.video.ended)
            or not can_ffmpeg
            or not self.get_child(".image_preview")
            or self.video.size is None
            or ((not self.video.file) or self.video.file != self._current_file_path)
            or not which(ffmpeg)
        ):
            return
        self.video.running = True
        self.video.token = object()
        self._update_video_subtitle()
        self._play_video(
            self.video.file,
            self.video.position,
            self.video.token,
            self._active_preview_token,
        )

    @work(thread=True, exclusive=True, group="video-playback")
    def _play_video(
        self: PreviewContainer,
        source: str,
        position: float,
        token: object,
        preview: object,
    ) -> None:
        context_token = self.preview_token.set(preview)
        process: subprocess.Popen[bytes] | None = None
        try:
            if self.video.duration is None:
                duration = self._probe_video_duration(source, os.stat(source))
                if duration is not None:
                    self.call_from_thread(self._set_video_duration, duration, token)
            if token is not self.video.token:
                return
            size = self.video.size
            if size is None:
                return
            process = subprocess.Popen(
                [ffmpeg, "-hide_banner", "-loglevel"]
                + ["error", "-nostdin", "-re", "-ss", str(position), "-i"]
                + [source, "-map", "0:v:0", "-an", "-sn", "-pix_fmt"]
                + ["rgb24", "-vf", f"fps={VIDEO_FPS},{VIDEO_SCALE_FILTER}"]
                + ["-f", "rawvideo", "pipe:1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if not self.call_from_thread(self._register_video_process, process, token):
                return
            assert process.stdout is not None
            # length * height * 3 (rgb)
            frame_size = size[0] * size[1] * 3
            frames = 0
            while True:
                data = bytearray()
                while len(data) < frame_size:
                    chunk = process.stdout.read(frame_size - len(data))
                    if not chunk:
                        # A partial frame or a terminated process is not a clean ending.
                        if not data and frames:
                            with contextlib.suppress(subprocess.TimeoutExpired):
                                if process.wait(timeout=0.5) == 0:
                                    self.call_from_thread(self._finish_video, token)
                        return
                    data.extend(chunk)
                frames += 1
                image = Image.frombytes("RGB", size, bytes(data))
                if not self.call_from_thread(
                    self._show_video_frame, image, position + frames / VIDEO_FPS, token
                ):
                    return
        except FileNotFoundError:
            self.notify(
                f"FFmpeg executable not found: {config['plugins']['ffmpeg']['ffmpeg_path']}.",
                title="Plugins: FFmpeg",
                severity="warning",
                markup=False,
            )
        except (utils.ExitNow, OSError, ValueError):
            pass
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=0.3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if process.stdout is not None:
                    with contextlib.suppress(OSError):
                        process.stdout.close()
            with contextlib.suppress(RuntimeError):
                self.app.call_from_thread(self._clear_video_process, process, token)
            self.preview_token.reset(context_token)

    def _set_video_duration(
        self: PreviewContainer, duration: float, token: object
    ) -> None:
        if token is self.video.token:
            self.video.duration = duration
            self._update_video_subtitle()

    def _finish_video(self: PreviewContainer, token: object) -> None:
        if token is self.video.token:
            self.video.ended = True
            self.video.running = False
            if self.video.duration is not None:
                self.video.position = self.video.duration
            self._update_video_subtitle()

    def _register_video_process(
        self: PreviewContainer, process: subprocess.Popen[bytes], token: object
    ) -> bool:
        if token is not self.video.token or not self.has_focus_within:
            return False
        self.video.process = process
        return True

    def _clear_video_process(
        self: PreviewContainer, process: subprocess.Popen[bytes] | None, token: object
    ) -> None:
        # An older worker must not clear the process started after a seek.
        if self.video.process is process:
            self.video.process = None
        if token is self.video.token:
            self.video.running = False
            self._update_video_subtitle()

    def _show_video_frame(
        self: PreviewContainer, image: PILImage, position: float, token: object
    ) -> bool:
        if token is not self.video.token or not self.has_focus_within:
            return False
        widget = self.get_child(".image_preview")
        if widget is None:
            return False
        widget.image = image
        self.video.position = position
        self._update_video_subtitle()
        return True

    def _seek_video(self: PreviewContainer, position: float) -> None:
        if self.video.duration is not None:
            position = min(position, max(0.0, self.video.duration - 1 / VIDEO_FPS))
        self.video.position = max(0.0, position)
        self.video.ended = False
        self._stop_video()
        self.call_after_refresh(self._start_video)
        self.set_timer(1, lambda: setattr(self.video, "seeking", None))

    def show_video_preview(self) -> None:
        if utils.should_cancel() or self._current_file_path is None:
            return
        self.set_border("title", "Video Preview")
        if not can_ffmpeg:
            self._current_content = "Video previews are disabled."
            self.mount_special_messages()
            return

        source = self._current_file_path
        realpath = path.realpath(source)
        stat_res = os.stat(realpath)
        sig = (ffmpeg, VIDEO_SCALE_FILTER)
        image = cache._load_image(realpath, "video", stat_res, sig)
        if image is None:
            try:
                result = subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
                    + ["-i", source, "-map", "0:v:0", "-frames:v", "1", "-vf"]
                    + [VIDEO_SCALE_FILTER, "-c:v", "png", "-f", "image2pipe", "pipe:1"],
                    capture_output=True,
                    check=True,
                    timeout=15,
                )
                with Image.open(BytesIO(result.stdout)) as frame:
                    image = frame.copy()
            except FileNotFoundError:
                self._current_content = (
                    f"Cannot preview video: FFmpeg executable not found: {ffmpeg}"
                )
                self.mount_special_messages()
                return
            except (OSError, ValueError) as exc:
                if utils.should_cancel():
                    return
                self._current_content = f"Cannot preview video: {exc}"
                self.mount_special_messages()
                return
            except subprocess.CalledProcessError as exc:
                if utils.should_cancel():
                    return
                self._current_content = f"Cannot preview video: FFmpeg returned {exc.returncode} with stderr:\n{exc.stderr.decode('utf-8', errors='ignore')}"
                self.mount_special_messages()
                return
            if utils.should_cancel():
                return
            cache._save_image(realpath, "video", stat_res, image, sig)
            utils.check_cancel()
        duration = self._probe_video_duration(source, stat_res)
        self.call_from_thread(setattr, self.video, "duration", duration)
        # The scaled thumbnail tells us how many RGB bytes each playback frame has.
        self.call_from_thread(setattr, self.video, "size", image.size)
        self.call_from_thread(self._display_image, image)
        self.call_from_thread(self._update_video_subtitle)
