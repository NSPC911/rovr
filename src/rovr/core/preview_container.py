from __future__ import annotations

import contextlib
import os
import re
import subprocess
from contextvars import ContextVar
from functools import partial
from io import BytesIO
from math import ceil
from os import path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import monotonic, time
from typing import Awaitable, Callable, Literal, TypeVar, cast, overload

import textual_image.renderable
import textual_image.widget
from PIL import Image, UnidentifiedImageError
from rich.text import Text
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.content import Content
from textual.css.query import NoMatches
from textual.dom import DOMNode
from textual.geometry import Region
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Static
from textual.widgets.selection_list import Selection
from textual.worker import Worker

from rovr.classes.mixins import Action, Actionable
from rovr.classes.preview_mixins import BatMixin, PDFHandler, PDFMixin
from rovr.classes.textual_options import (
    ArchiveFileListSelection,
    FileListSelectionWidget,
)
from rovr.classes.type_aliases import CacheSource
from rovr.components import iterm2_image
from rovr.components.text_preview import (
    WindowedTextPreview,
    _decode_text_preview,
)
from rovr.core import FileList
from rovr.functions import cache, preview_utils, utils
from rovr.functions import icons as icon_utils
from rovr.functions import path as path_utils
from rovr.functions.ansi import ansi_to_rich_text
from rovr.variables.constants import (
    PREVIEWER_GROUP,
    RESAMPLING_METHOD,
    RESVG_CACHE_SIGNATURE,
    TEXT_PREVIEW_CACHE_VERSION,
    config,
    file_one,
    titles,
)

T = TypeVar("T")

# to any ai models looking at this, shut the fuck up
# yes i know this is a hidden module, and yes, i will
# continue using it, because i cant use a variable
# (the variable being textual_image.widget.Image)
image_protocol = config["interface"]["image_viewer"]["protocol"]
image_widget = (
    iterm2_image.ITerm2Image
    if (
        image_protocol == "ITerm2"
        or (image_protocol == "Auto" and iterm2_image.is_supported())
    )
    else textual_image.widget.__dict__[
        ("" if image_protocol == "Auto" else image_protocol) + "Image"
    ]
)


class LoadingPreview(Static):
    """Make the preview look empty"""

    def __init__(self) -> None:
        self.status = "Loading..."
        self.spinner_index = -1
        super().__init__()
        self.timer_enabled = False

    def on_mount(self) -> None:
        assert isinstance(self.parent, PreviewContainer)
        # sad thing is that you cant just raw-dog `self.styles` = `self.parent.styles`
        self.border_title = self.parent.border_title
        self.border_subtitle = self.parent.border_subtitle
        self.styles.border = self.parent.styles.border
        self.styles.background = self.parent.styles.background
        self.can_focus = True
        spinner = config["interface"]["spinner"]
        self.spinner_index = (self.spinner_index + 1) % len(spinner)
        self.update(f"{spinner[self.spinner_index]} {self.status}")
        if not self.timer_enabled:
            self.timer_enabled = True
            self.set_interval(0.25, self.on_mount)

    def set_status(self, status: str) -> None:
        self.status = status
        spinner = config["interface"]["spinner"]
        spinner_index = max(self.spinner_index, 0)
        self.update(f"{spinner[spinner_index]} {self.status}")

    async def on_event(self, event: events.Event) -> None:
        self.on_mount()


class PreviewContainer(Actionable, PDFMixin, BatMixin, Container):
    key_contexts = ("preview", "scroll")
    ALLOW_MAXIMIZE = True
    LOADER_WIDGET = LoadingPreview()

    ACTIONS: list[Action] = [
        Action(action, config["keybinds"][action])
        for action in ("up", "down", "page_up", "page_down", "home", "end")
    ]

    preview_token: ContextVar[object] = ContextVar("preview_token")
    IMAGE_CACHE_SIGNATURE = (
        f"{preview_utils.MAX_IMAGE_SIZE[0]}x{preview_utils.MAX_IMAGE_SIZE[1]}",
        str(RESAMPLING_METHOD()),
    )
    NewImage = staticmethod(partial(image_widget, classes="image_preview"))

    def __init__(self) -> None:
        super().__init__(id="preview_sidebar")
        self._loading_timer: Timer | None = None
        self._pending_preview_args: tuple[str, int | float] | None = None
        self._current_content: str | list[str] | None = None
        self._current_file_path: str | None = None
        self._file_type: str = "none"
        self._file_mtime: float | None = None
        self._rendered_preview_key: tuple[str, float] | None = None
        self._mime_type: preview_utils.MimeResult | None = None
        self._preview_texts = config["interface"]["preview_text"]
        self._active_preview_token = object()
        self.pdf = PDFHandler()
        self._video_source: tuple[str, float] | None = None
        self._video_position = 0
        self._video_duration: float | None = None

    def compose(self) -> ComposeResult:
        yield Static(self._preview_texts["start"], classes="special")

    def on_mount(self) -> None:
        self.watch(self.screen, "maximized", self._on_maximized, init=False)

    def _on_maximized(self, widget: Widget | None) -> None:
        if widget is None or (widget is not self and self not in widget.ancestors):
            return
        if widget is not self:
            # Maximizing a focused image would leave the rest of the preview behind.
            self.screen.maximized = self
        else:
            self.call_after_refresh(self._focus_if_maximized)

    def _focus_if_maximized(self) -> None:
        if (
            self.screen.is_active
            and self.screen.maximized is self
            and not self.has_focus_within
        ):
            self.focus()

    def get_loading_widget(self) -> LoadingPreview:
        """Get a widget to display a loading indicator.

        Returns:
            A widget in place of this widget to indicate a loading.
        """
        self.LOADER_WIDGET = LoadingPreview()
        return self.LOADER_WIDGET

    def get_child(self, selector: str | type[DOMNode]) -> DOMNode | None:
        """
        Check for whether this element contains this selector and return the element if it does.
        Args:
            selector(str): the selector to test

        Returns:
            DOMNode: the element if it exists
            None: if it doesn't exist
        """
        try:
            return self.query_one(selector)
        except NoMatches:
            return None

    def set_border(self, title: Literal["title", "subtitle"], to: str) -> None:
        """Set the border title or subtitle of this widget.

        Args:
            title: "title" or "subtitle"
            to: The string to set the title/subtitle to.

        Raises:
            ExitNow: If this preview request is no longer active.
        """
        func = lambda: setattr(self, "border_" + title, to)
        try:
            self.call_from_thread(func)
        except utils.ExitNow:
            raise
        except (RuntimeError, LookupError):
            func()

    @on(Worker.StateChanged)
    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.group != PREVIEWER_GROUP:
            return
        loading_state = any(
            worker.node is self and worker.group == PREVIEWER_GROUP and worker.is_running
            for worker in self.workers
        )
        if loading_state and self.loading:
            return
        elif loading_state and not self.loading:
            if self._loading_timer is None:
                self._loading_timer = self.set_timer(
                    0.25,
                    lambda self=self: (
                        self.set_loading(True)
                        if not self.loading
                        and any(
                            worker.node is self
                            and worker.group == PREVIEWER_GROUP
                            and worker.is_running
                            for worker in self.workers
                        )
                        else None
                    ),
                )
        else:
            if self._loading_timer is not None:
                self._loading_timer.stop()
                self._loading_timer = None
            self.set_loading(False)

    async def file_not_found(
        self, location: str, highlighted_option: FileListSelectionWidget | None = None
    ) -> None:
        # prevent short circuit from occurring later on
        if utils.should_cancel():
            return
        self._current_file_path = None
        self._rendered_preview_key = None
        self._file_mtime = None
        self._file_type = "none"
        self._mime_type = None

        if not (static := self.get_child(".special")):
            async with self.batch():
                await self.remove_children()
                await self.mount(static := Static("", classes="special", markup=False))

        self.set_border("title", "")
        self.set_border("subtitle", "")
        dir_entry = path_utils.get_direntry_for(location)
        if not dir_entry:
            # lowk just skip
            return
        try:
            if dir_entry.is_symlink():
                self.set_border("title", "Broken Symlink")
                try:
                    target_path = os.readlink(location)
                    msg = f"The symlink target is not found!\nTarget: {target_path}"
                except OSError:
                    msg = "The symlink target is not found!"

                static.update(msg)

                # also update option if necessary
                if isinstance(
                    highlighted_option, FileListSelectionWidget
                ) and highlighted_option.icon != icon_utils.get_icon(
                    "general", "broken_symlink"
                ):
                    highlighted_option.set_icon(
                        icon_utils.get_icon("general", "broken_symlink")
                    )
            else:
                static.update("This file no longer exists...")
        except FileNotFoundError:
            # if the thing itself is gone basically
            static.update("This file no longer exists...")

    def show_font_preview(self) -> None:
        """Show font preview with PIL.ImageFont and a custom PIL.ImageDraw.

        Raises:
            ExitNow: If this preview request is no longer active.
        """
        from PIL import ImageDraw, ImageFont
        from textual.color import Color

        if utils.check_cancel() or self._current_file_path is None:
            return

        self.set_border("title", titles.font)

        fg_color = Color.parse(self.app.theme_variables["foreground"])
        bg_color = Color.parse(self.app.theme_variables["background"])
        realpath = path.realpath(self._current_file_path)
        try:
            stat_res = os.stat(realpath)
        except FileNotFoundError:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(self._preview_texts["error"], classes="special", markup=False),
            )
            return
        sig = (
            f"{preview_utils.MAX_FONT_SIZE}:{config['interface']['font_preview']['font_size']}",
            f"{self._preview_texts['font_text']}:{fg_color.hex}:{bg_color.hex}:{self.NewImage.func.__name__}",
        )
        img = cache._load_image(realpath, "font", stat_res, sig)
        if img is not None:
            if image_widget := self.get_child(".image_preview"):
                self.call_from_thread(setattr, image_widget, "image", img)
            else:
                self.call_from_thread(self.remove_children)
                image_widget = self.NewImage(img)
                image_widget.can_focus = True
                self.call_from_thread(self.mount, image_widget)
            return

        text_fill: tuple[int, ...]
        # need to do this weird check because sixel doesn't support transparency
        # so just check whether auto renderer is sixel, and config configured
        # to use auto (empty string) or sixel (explicitly)
        if (
            self.NewImage.func is textual_image.renderable.sixel.Image
            # image_viewer.protocol shouldn't be "Auto" because it is replaced early on
            # when loading the config, but just for the sake of shutting AI
            # up, I'm going to leave this here.
        ):
            img = Image.new(
                "RGB",
                (preview_utils.MAX_FONT_SIZE[0], preview_utils.MAX_FONT_SIZE[1]),
                color=(bg_color.r, bg_color.g, bg_color.b),
            )
            text_fill = (fg_color.r, fg_color.g, fg_color.b)
        else:
            img = Image.new(
                "RGBA",
                (preview_utils.MAX_FONT_SIZE[0], preview_utils.MAX_FONT_SIZE[1]),
                color=(0, 0, 0, 0),
            )
            text_fill = (fg_color.r, fg_color.g, fg_color.b, 255)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(
                self._current_file_path,
                size=config["interface"]["font_preview"]["font_size"],
            )
            utils.check_cancel()
        except OSError:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(
                    "Cannot load font. The file may be corrupted or not a font file.",
                    classes="special",
                ),
            )
            return
        text = self._preview_texts["font_text"]
        # used for centering
        bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        width, height = img.size

        draw.multiline_text(
            (
                (width - text_width) // 2 - bbox[0],
                (height - text_height) // 2 - bbox[1],
            ),
            text,
            font=font,
            fill=text_fill,
        )
        cache._save_image(realpath, "font", stat_res, img, sig)
        utils.check_cancel()

        try:
            if image_widget := self.get_child(".image_preview"):
                self.call_from_thread(setattr, image_widget, "image", img)
            else:
                self.call_from_thread(self.remove_children)

                utils.check_cancel()

                image_widget = self.NewImage(img)
                # no need to resample, already ensured that canvas is max size
                image_widget.can_focus = True
                self.call_from_thread(self.mount, image_widget)
        except utils.ExitNow:
            raise
        except Exception as exc:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(
                    f"Cannot render font preview.\n{type(exc).__name__}: {str(exc)}",
                    classes="special",
                    markup=False,
                ),
            )
            return

    def show_resvg_preview(self) -> None:
        """Show svg preview using resvg.

        Raises:
            ExitNow: If this preview request is no longer active.
            ValueError: If SVG loading fails for non-fds_to_keep reasons.
        """
        if utils.check_cancel() or self._current_file_path is None:
            return
        self.set_border("title", titles.svg)

        # load svg as bytes
        try:
            realpath = path.realpath(self._current_file_path)
            stat_res = os.stat(realpath)
            pil_object = cache._load_image(
                realpath,
                "svg",
                stat_res,
                sig=RESVG_CACHE_SIGNATURE,
            )
            if pil_object is None:
                self.call_next(self.LOADER_WIDGET.set_status, "loading svg...")
                if self.app.MULTIPROCESSING_PROCESS_ALLOWED:
                    try:
                        png_bytes = preview_utils.load_svg(realpath)
                    except ValueError as exc:
                        if utils.multiprocessing_process_error_checker(self.app, exc):
                            png_bytes = preview_utils.load_svg_sync(realpath)
                        else:
                            raise
                else:
                    png_bytes = preview_utils.load_svg_sync(realpath)
                if png_bytes is None:
                    self.notify(
                        "Failed to load SVG. The file may be corrupted or not an SVG file.",
                        title="SVG Preview",
                        severity="error",
                    )
                    self.call_from_thread(self.remove_children)
                    self.set_border("title", "")
                    return
                elif png_bytes == b"cancelled":
                    return

                utils.check_cancel()

                self.call_next(self.LOADER_WIDGET.set_status, "resampling svg...")

                if self.app.MULTIPROCESSING_PROCESS_ALLOWED:
                    try:
                        pil_object = preview_utils.resample(
                            Image.open(BytesIO(png_bytes))
                        )
                    except ValueError as exc:
                        if utils.multiprocessing_process_error_checker(self.app, exc):
                            pil_object = preview_utils.resample_sync(
                                Image.open(BytesIO(png_bytes))
                            )
                        else:
                            raise
                else:
                    pil_object = preview_utils.resample_sync(
                        Image.open(BytesIO(png_bytes))
                    )
                cache._save_image(
                    realpath,
                    "svg",
                    stat_res,
                    pil_object,
                    sig=RESVG_CACHE_SIGNATURE,
                )

            utils.check_cancel()

            if image_widget := self.get_child(".image_preview"):
                self.call_from_thread(setattr, image_widget, "image", pil_object)
            else:
                self.call_from_thread(self.remove_children)

                utils.check_cancel()

                image_widget = self.NewImage(pil_object)
                image_widget.can_focus = True
                self.call_from_thread(self.mount, image_widget)
        except ValueError as exc:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(
                    f"Cannot render svg.\n{str(exc)}", classes="special", markup=False
                ),
            )
            return
        except utils.ExitNow:
            raise
        except Exception as exc:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(
                    f"Cannot render svg.\n{type(exc).__name__}: {str(exc)}",
                    classes="special",
                    markup=False,
                ),
            )
            return

    def show_image_preview(
        self,
        magicked: bool = False,
        title: bool = True,
        cache_source: CacheSource | None = None,
    ) -> None:
        """Show image preview. Runs in a thread.

        Raises:
            ValueError: If image loading fails for non-fds_to_keep reasons.
        """
        if utils.check_cancel() or self._current_file_path is None:
            return
        if title:
            self.set_border("title", titles.image)

        try:
            realpath, stat_res, sig = cache_source or (
                path.realpath(self._current_file_path),
                os.stat(self._current_file_path),
                self.IMAGE_CACHE_SIGNATURE,
            )
            cache_type = "custom-image" if cache_source else "image"
            pil_object = cache._load_image(realpath, cache_type, stat_res, sig)
            if pil_object is None:
                if self.app.MULTIPROCESSING_PROCESS_ALLOWED:
                    try:
                        pil_object = preview_utils.resample_file(self._current_file_path)
                    except ValueError as exc:
                        if utils.multiprocessing_process_error_checker(self.app, exc):
                            pil_object = preview_utils.resample_file_sync(
                                self._current_file_path
                            )
                        else:
                            raise
                else:
                    pil_object = preview_utils.resample_file_sync(self._current_file_path)
                if pil_object is None:
                    return
                cache._save_image(realpath, cache_type, stat_res, pil_object, sig)
        except (UnidentifiedImageError, NotImplementedError) as exc:
            utils.check_cancel()
            from shutil import which

            if (
                not magicked
                and config["plugins"]["magick"]["enabled"]
                and which(config["plugins"]["magick"]["executable"])
            ):
                cache_path = cache._cache_path(realpath, cache_type, stat_res, sig)
                try:
                    proc = subprocess.run(
                        [
                            config["plugins"]["magick"]["executable"],
                            # TODO: multi-image heics are a thing, how to support?
                            # refactor pdf to be more generic?
                            self._current_file_path + "[0]",
                            "-resize",
                            f"{preview_utils.MAX_IMAGE_SIZE[0]}x{preview_utils.MAX_IMAGE_SIZE[1]}>",
                            cache_path + ".png",
                        ],
                        capture_output=True,
                        timeout=15,
                    )
                    if proc.returncode == 0:
                        os.replace(cache_path + ".png", cache_path)
                        self.show_image_preview(True, title, cache_source)
                        return
                except subprocess.TimeoutExpired:
                    pass
                except FileNotFoundError:
                    self.notify(
                        "ImageMagick executable not found. Please check your configuration.",
                        title="ImageMagick Error",
                        severity="error",
                    )
                if os.path.exists(cache_path + ".png"):
                    os.remove(cache_path + ".png")
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(
                    f"Cannot render image (is the encoding wrong?)\nMIME Type: {self._mime_type}"
                    if isinstance(exc, UnidentifiedImageError)
                    else f"Cannot render image\nContains {exc}",
                    classes="special",
                    markup=False,
                ),
            )
            return
        except FileNotFoundError:
            utils.check_cancel()
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                self.mount,
                Static(self._preview_texts["error"], classes="special", markup=False),
            )
            return

        if image_widget := self.get_child(".image_preview"):
            utils.check_cancel()
            self.call_from_thread(setattr, image_widget, "image", pil_object)
        else:
            self.call_from_thread(self.remove_children)

            utils.check_cancel()

            image_widget = self.NewImage(pil_object)
            image_widget.can_focus = True
            self.call_from_thread(self.mount, image_widget)

            utils.check_cancel()

    def show_normal_file_preview(self) -> None:
        """Show normal file preview with syntax highlighting. Runs in a thread.

        Raises:
            ExitNow: If this preview request is no longer active.
        """
        utils.check_cancel()

        self.set_border("title", titles.file)

        if self._current_file_path is None:
            raise utils.ExitNow()
        realpath = path.realpath(self._current_file_path)
        stat_res = os.stat(realpath)
        max_file_size = config["interface"]["preview_text"]["max_file_size"]
        sig = (str(max_file_size), TEXT_PREVIEW_CACHE_VERSION)
        content: str | None = cache.load(
            realpath,
            "windowed_text",
            stat_res,
            sig,
            pass_as=str,
        )
        if content is None:
            try:
                with open(realpath, "rb") as file:
                    raw_content = file.read(max_file_size)
                    ignored_bytes = stat_res.st_size - len(raw_content)
            except FileNotFoundError:
                return

            decoded = _decode_text_preview(raw_content, ignored_bytes > 0)
            if decoded is None:
                content = None
            else:
                content, incomplete_bytes = decoded
                ignored_bytes += incomplete_bytes
                if ignored_bytes:
                    if not content.endswith("\n"):
                        content += "\n"
                    content += (
                        f"---\n({ignored_bytes:,} byte{utils.s(ignored_bytes)} ignored)"
                    )
                cache.save(realpath, "windowed_text", stat_res, sig, content)

        if content is None:
            self._current_content = self._preview_texts["error"]
            self.mount_special_messages()
            return

        lines = content.splitlines() or [""]
        sample_parts: list[str] = []
        sample_length = 0
        for line in lines:
            remaining = 4096 - sample_length
            if remaining <= 0:
                break
            sample_parts.append(line[:remaining])
            sample_length += len(sample_parts[-1])
        sample = "".join(sample_parts)
        from textual.highlight import guess_language

        language: str = guess_language(sample, path=self._current_file_path) or "text"
        utils.check_cancel()

        if text_preview := self.get_child(WindowedTextPreview):
            self.call_from_thread(
                text_preview.update_preview,
                lines,
                language=language,
                line_numbers=config["interface"]["show_line_numbers"],
            )
            self.call_from_thread(text_preview.set_classes, "text_preview")
        else:
            self.call_from_thread(self.remove_children)

            utils.check_cancel()

            self.call_from_thread(
                lambda: self.mount(
                    WindowedTextPreview(
                        lines,
                        language=language,
                        line_numbers=config["interface"]["show_line_numbers"],
                        classes="text_preview",
                    ).data_bind(type(self.app).ansi_color)
                )
            )

        utils.check_cancel()

    def show_folder_preview(self, folder_path: str) -> None:
        """Show folder preview."""
        utils.check_cancel()

        self.set_border("title", titles.folder)

        if not (this_list := self.get_child("FileList")):
            self.call_from_thread(self.remove_children)

            utils.check_cancel()

            this_list = FileList(
                name=folder_path,
                classes="file-list",
                dummy=True,
                enter_into=folder_path,
            )
            self.call_from_thread(self.mount, this_list)

        utils.check_cancel()

        assert isinstance(this_list, FileList)
        this_list.enter_into = folder_path

        self.call_from_thread(this_list.set_classes, "file-list")

        # Query StateManager for sort preferences for the previewed folder
        from rovr.functions.path import normalise
        from rovr.state_manager import StateManager

        state_manager: StateManager = self.app.query_one(StateManager)
        normalised_path = normalise(folder_path)
        sort_by, sort_descending = state_manager.get_sort_prefs(normalised_path)
        options = []
        loading_timer = self.call_from_thread(
            self.set_timer,
            0.25,
            lambda: setattr(self, "border_subtitle", "Getting list\u2026"),
        )
        try:
            folders, files = path_utils.sync_get_cwd_object(
                self,
                folder_path,
                config["interface"]["show_hidden_files"],
                sort_by=sort_by,
                reverse=sort_descending,
                return_nothing_if_this_returns_true=utils.should_cancel,
            )
            if files is None or folders is None:
                return
            if not (folders or files):
                options = [Selection("  --no-files--", value="", id="", disabled=True)]
            else:
                file_list_options = folders + files
                file_list_option_length = len(file_list_options)
                start_time = time()
                for index, item in enumerate(file_list_options):
                    options.append(
                        FileListSelectionWidget(
                            icon_factory=item["icon"],
                            label=item["name"],
                            dir_entry=item["dir_entry"],
                            clipboard=self.app.Clipboard,
                        )
                    )
                    if start_time + 0.25 < time():
                        self.set_border(
                            "subtitle", f"{index + 1} / {file_list_option_length}"
                        )
                        start_time = time()
                        utils.check_cancel()
        except OSError as exc:
            options = [
                Selection(
                    f" {exc.strerror} (err no {exc.errno})",
                    id="",
                    value="",
                    disabled=True,
                )
            ]
        finally:
            loading_timer.stop()
        utils.check_cancel()
        self.set_border("subtitle", "")
        self.call_from_thread(this_list.set_options, options)

    def show_archive_preview(self) -> None:
        """Show archive preview."""
        utils.check_cancel()
        self.set_border("title", titles.archive)

        if not (file_list := self.get_child("FileList")):
            self.call_from_thread(self.remove_children)

            utils.check_cancel()

            file_list = FileList(
                classes="archive-list",
                dummy=True,
            )

            self.call_from_thread(self.mount, file_list)

        utils.check_cancel()

        assert isinstance(file_list, FileList)

        self.call_from_thread(file_list.set_classes, "archive-list")
        options = []
        if not self._current_content:
            options = [Selection("  --no-files--", value="", id="", disabled=True)]
        else:

            def get_archive_icon(target_file_path: str) -> tuple[str, str]:
                if target_file_path.endswith("/"):
                    return icon_utils.get_icon_for_folder(target_file_path.strip("/"))
                return icon_utils.get_icon_for_file(target_file_path)

            file_list_length = len(self._current_content)
            start_time = time()
            for index, file_path in enumerate(self._current_content):
                options.append(
                    ArchiveFileListSelection(
                        lambda file_path=file_path: get_archive_icon(file_path),
                        file_path,
                    )
                )
                if start_time + 0.25 < time():
                    self.set_border("subtitle", f"{index + 1} / {file_list_length}")
                    start_time = time()
                    utils.check_cancel()

        utils.check_cancel()
        self.call_from_thread(file_list.set_options, options)
        self.set_border("subtitle", "")

    def show_preview(self, file_path: str, mtime: int | float) -> None:
        """Public method to show preview."""
        if self._video_source != (file_path, mtime):
            self._video_source = (file_path, mtime)
            self._video_position = 0
            self._video_duration = None
        token = self._active_preview_token = object()
        if (
            "hide" in self.classes
            or "-no-preview" in self.screen.classes
            or "-filelist-only" in self.screen.classes
        ):
            self._pending_preview_args = (file_path, mtime)
            self.call_after_refresh(self._compute_and_sync_mime, file_path, mtime, token)
            return
        self._pending_preview_args = None
        self.perform_show_preview(file_path, mtime, token)

    @overload
    def call_from_thread(
        self, func: Callable[..., Awaitable[T]], *args, **kwargs
    ) -> T: ...

    @overload
    def call_from_thread(self, func: Callable[..., T], *args, **kwargs) -> T: ...

    def call_from_thread(
        self, func: Callable[..., T | Awaitable[T]], *args, **kwargs
    ) -> T:
        token = self.preview_token.get()

        def guarded() -> T | Awaitable[T]:
            if token is not self._active_preview_token:
                raise utils.ExitNow()
            return func(*args, **kwargs)

        return cast(T, self.app.call_from_thread(guarded))

    @work(thread=True, exclusive=True, group=PREVIEWER_GROUP)
    def _compute_and_sync_mime(
        self, file_path: str, mtime: int | float, token: object
    ) -> None:
        context_token = self.preview_token.set(token)
        try:
            utils.check_cancel()
            if token is not self._active_preview_token:
                return
            mime_type = (
                preview_utils.MimeResult("basic", "inode/directory")
                if path.isdir(file_path)
                else preview_utils.get_mime_type(file_path, mtime)
            )
            utils.check_cancel()
            self.call_from_thread(self._sync_mime, file_path, mime_type)
        except utils.ExitNow:
            pass
        finally:
            self.preview_token.reset(context_token)

    @work(exclusive=True, thread=True, group=PREVIEWER_GROUP)
    def perform_show_preview(
        self, file_path: str, mtime: int | float, token: object
    ) -> None:
        """Main preview worker. Runs in a thread."""
        context_token = self.preview_token.set(token)
        try:
            utils.check_cancel()

            if self._rendered_preview_key is not None:
                # check mtime as well
                try:
                    new_mtime = path.getmtime(file_path)
                except FileNotFoundError:
                    # if file is gone/symlink target is gone
                    self.call_from_thread(self.file_not_found, file_path)
                    return
                if self._rendered_preview_key == (file_path, new_mtime):
                    return

            self.call_from_thread(setattr, self, "_rendered_preview_key", None)
            if self._file_type != "video" or (file_path, mtime) != (
                self._current_file_path,
                self._file_mtime,
            ):
                self.set_border("subtitle", "")
            utils.check_cancel()

            # Reset PDF state when changing files
            if file_path != self._current_file_path:
                self.pdf.images = None
                self.pdf.current_page = 0
                self.pdf.total_pages = 0

            if path.isdir(file_path):
                mime_type = preview_utils.MimeResult("basic", "inode/directory")
                file_type = preview_utils.match_mime_to_preview_type(mime_type.mime_type)
                if file_type == "folder" or file_type in config["settings"].get(
                    "previewers", {}
                ):
                    self.update_ui(
                        file_path=file_path, mime_type=mime_type, file_type=file_type
                    )
                else:
                    self.notify(
                        f"MIME type `inode/directory` must use `folder` preview type.\nGot {file_type=} (expected `folder`)",
                        title="Preview Error",
                        severity="error",
                    )
            else:
                content = None  # for now
                file_extension = path.splitext(file_path)[1]
                mime_result = preview_utils.get_mime_type(file_path, mtime)
                self.log(mime_result)
                if mime_result is None:
                    self.log(f"Could not get MIME type for {file_path}")
                    self.update_ui(
                        file_path=file_path,
                        file_type="file",
                        content=self._preview_texts["error"],
                    )
                    return
                utils.check_cancel()
                file_type = preview_utils.match_mime_to_preview_type(
                    mime_result.mime_type, file_extension
                )
                if file_type is None:
                    self.log("Could not match MIME type to preview type")
                    self.update_ui(
                        file_path=file_path,
                        file_type="file",
                        mime_type=mime_result,
                        content=self._preview_texts["error"],
                    )
                    return
                elif file_type == "remime":
                    mime_result = preview_utils.get_mime_type(
                        file_path, mtime, ("basic", "puremagic")
                    )
                    if mime_result is None:
                        self.log("Could not get MIME type for remime")
                        self.update_ui(
                            file_path=file_path,
                            file_type="file",
                            content=self._preview_texts["error"],
                            mime_type=mime_result,
                        )
                        return
                    file_type = preview_utils.match_mime_to_preview_type(
                        mime_result.mime_type, file_extension
                    )
                    if file_type is None:
                        self.log("Could not match MIME type to preview type")
                        self.update_ui(
                            file_path=file_path,
                            file_type="file",
                            mime_type=mime_result,
                            content=self._preview_texts["error"],
                        )
                        return
                self.log(f"Previewing as {file_type} (MIME: {mime_result.mime_type})")

                if file_type == "archive":
                    from multiarchive._archive import Archive, BadArchiveError

                    realpath = path.realpath(file_path)
                    stat_res = os.stat(realpath)
                    content: list[str] | None = cache.load(
                        realpath,
                        "archive",
                        stat_res,
                        ("json", "utf-8"),
                        pass_as=list,
                    )
                    if content is None:
                        try:
                            with Archive(file_path, mode="r") as archive:
                                self.set_border("title", titles.archive)
                                all_files = []
                                for member in archive.infolist():
                                    utils.check_cancel()

                                    if not member.is_dir:
                                        all_files.append(member.name)
                            content = all_files
                            cache.save(
                                realpath,
                                "archive",
                                stat_res,
                                ("json", "utf-8"),
                                all_files,
                            )
                        except (
                            BadArchiveError,
                            ValueError,
                            FileNotFoundError,
                            EOFError,
                        ):
                            content = [self._preview_texts["error"]]

                self.update_ui(
                    file_path,
                    file_type=file_type,
                    content=content,
                    mime_type=mime_result,
                )

            utils.check_cancel()
        except (IsADirectoryError, NotADirectoryError):
            pass
        except utils.ExitNow:
            return
        except subprocess.CalledProcessError as exc:
            if utils.should_cancel():
                return
            assert self._current_file_path is not None
            self._current_content = (
                f"CalledProcessError:\n{exc}\n"
                f"stdout:\n{exc.stdout.decode('utf-8', errors='ignore')}\n"
                f"stderr:\n{exc.stderr.decode('utf-8', errors='ignore')}"
            )
            self.mount_special_messages(mime=False)
            path_utils.dump_exc(self, exc)
        except Exception as exc:
            if isinstance(exc, OSError) and "cannot be accessed by the system" in str(
                exc.strerror
            ):
                self.call_from_thread(self.remove_children)
                return
            elif isinstance(exc, FileNotFoundError):
                self.call_from_thread(self.file_not_found, file_path)
                return
            self.notify(
                f"{type(exc).__name__} was raised while generating the preview\n{str(exc)}",
                severity="error",
                markup=False,
            )
            path_utils.dump_exc(self, exc)
        finally:
            self.preview_token.reset(context_token)

    def update_ui(
        self,
        file_path: str,
        file_type: str,
        content: str | list[str] | None = None,
        mime_type: preview_utils.MimeResult | None = None,
    ) -> None:
        mtime = path.getmtime(file_path)

        self._current_file_path = file_path
        self._current_content = content
        self._mime_type = mime_type
        self._file_mtime = path.getmtime(file_path)
        self._file_type = file_type

        self.call_after_refresh(self._sync_mime, file_path, mime_type)

        self.call_from_thread(self.remove_class, "pdf")
        if file_type == "folder":
            self.log("Showing folder preview")
            self.show_folder_preview(file_path)
        elif file_type == "image":
            self.log("Showing image preview")
            self.show_image_preview()
        elif file_type == "video":
            self.show_video_preview(file_path, self._video_position)
        elif file_type == "archive":
            self.log("Showing archive preview")
            self.show_archive_preview()
        elif file_type == "pdf":
            self.log("Showing pdf preview")
            self.call_from_thread(self.add_class, "pdf")
            self.show_pdf_preview()
        elif file_type == "resvg":
            self.log("Showing resvg preview")
            self.show_resvg_preview()
        elif file_type == "font":
            self.log("Showing font preview")
            self.show_font_preview()
        elif file_type == "details":
            self._current_content = ""
            self.mount_special_messages()
        elif content in self._preview_texts.values():
            self.log("Showing special preview")
            self.mount_special_messages()
        elif file_type in config["settings"].get("previewers", {}):
            self.log(f"Showing custom previewer for {file_type}")
            self.show_custom_preview(file_type)
        elif file_type not in ("text", "remime"):
            # means custom previewer is not set, and it isnt the next previewer (text)
            # im also including remime because it can happen if remime occurs twice
            # which means it is a really short file (hence file1 cant identify) and
            # gives it application/octet-stream twice, so yeah i guess
            self.notify(
                f"{file_type!r} previewer is not set",
                title="Preview Error",
                severity="error",
                markup=False,
            )
            self._current_content = ""
            self.mount_special_messages(mime=True)
        elif not (config["plugins"]["bat"]["enabled"] and self.show_bat_file_preview()):
            self.show_normal_file_preview()

        if not utils.should_cancel():
            self.call_from_thread(
                setattr, self, "_rendered_preview_key", (file_path, mtime)
            )

    def show_custom_preview(self, name: str) -> None:
        previewer = config["settings"]["previewers"][name]
        self.set_border("title", f"{name} Previewer")
        original_path = self._current_file_path
        assert original_path is not None

        with NamedTemporaryFile(
            delete=False, suffix=path.splitext(original_path)[1]
        ) as temp:
            temp_path = temp.name

        def expand_temp(value: str) -> str:
            return re.sub(
                r"%temp(?:\.[a-zA-Z0-9]+)?",
                lambda match: (
                    path.splitext(temp_path)[0] + match.group()[5:]
                    if match.group() != "%temp"
                    else temp_path
                ),
                value,
            )

        output = previewer.get("file", "__stdout__")
        output_path = expand_temp(output)
        try:
            realpath = path.realpath(original_path)
            stat_res = os.stat(realpath)
            sig = (name, repr(previewer))
            is_text = previewer["type"] == "text"
            output_data: Text | bytes | None = (
                cache._load_text(realpath, "custom-previewer-text", stat_res, sig)
                if is_text
                else cache.load(realpath, "custom-previewer", stat_res, sig)
            )
            if output_data is None:
                command = self.call_from_thread(
                    utils.expand_command,
                    self.app,
                    previewer["command"],
                    ["%clip", "%s", "%rs", "%tab"],
                )
                if output in ("__stdout__", "__stderr__") and "%file" in str(command):
                    raise ValueError("%file requires a previewer output path")
                with contextlib.ExitStack() as stack:
                    tmpdir = (
                        stack.enter_context(TemporaryDirectory())
                        if "%tmpdir" in str(command)
                        else ""
                    )

                    def expand_part(part: str) -> str:
                        return (
                            expand_temp(part)
                            .replace("%file", output_path)
                            .replace("%tmpdir", tmpdir)
                        )

                    if isinstance(command, str):
                        command = expand_part(command)
                    else:
                        command = [expand_part(part) for part in command]

                    process = subprocess.run(
                        command,
                        capture_output=True,
                        shell=isinstance(command, str),
                        check=True,
                        timeout=60,  # very reasonable time
                    )

                if output == "__stdout__":
                    output_data = process.stdout
                elif output == "__stderr__":
                    output_data = process.stderr
                elif path.exists(output_path):
                    with open(output_path, "rb") as file:
                        output_data = file.read()
                else:
                    self.notify(
                        f"Path = {output_path} does not exist",
                        title="Custom Previewer",
                        severity="error",
                        markup=False,
                    )
                    self._current_content = (
                        f"Custom previewer output path does not exist: {output_path}"
                    )
                    self.mount_special_messages(mime=True)
                    return

                if is_text:
                    output_data = ansi_to_rich_text(
                        output_data.decode("utf-8", errors="replace")
                    )
                    cache._save_text(
                        realpath,
                        "custom-previewer-text",
                        stat_res,
                        sig,
                        output_data,
                    )
                else:
                    cache.save(
                        realpath,
                        "custom-previewer",
                        stat_res,
                        sig,
                        output_data,
                    )

            utils.check_cancel()
            match previewer["type"]:
                case "text":
                    assert isinstance(output_data, Text)
                    self.show_custom_text_preview(output_data)
                case "image":
                    assert isinstance(output_data, bytes)
                    self._current_file_path = cache._cache_path(
                        realpath, "custom-previewer", stat_res, sig
                    )
                    self.show_image_preview(
                        title=False,
                        cache_source=(
                            realpath,
                            stat_res,
                            (name, f"{repr(previewer)}:{self.IMAGE_CACHE_SIGNATURE}"),
                        ),
                    )
                case "pdf":
                    assert isinstance(output_data, bytes)
                    self._current_file_path = cache._cache_path(
                        realpath, "custom-previewer", stat_res, sig
                    )
                    self.show_pdf_preview(
                        title=False,
                        cache_source=(
                            realpath,
                            stat_res,
                            (
                                name,
                                f"{repr(previewer)}:{config['plugins']['poppler']['use_pdftocairo']}",
                            ),
                        ),
                    )

        except FileNotFoundError:
            if utils.should_cancel():
                return
            self.notify(
                f"Previewer Executable not found: {previewer['command'][0] if isinstance(previewer['command'], list) else previewer['command']}",
                title=f"Custom Previewer: {name}",
                severity="error",
                markup=False,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            if utils.should_cancel():
                return
            msg = (
                (
                    f"Custom previewer command failed with exit code {exc.returncode}\n"
                    f"stdout:\n{exc.stdout.decode('utf-8', errors='ignore')}\n"
                    f"stderr:\n{exc.stderr.decode('utf-8', errors='ignore')}"
                )
                if isinstance(exc, subprocess.CalledProcessError)
                else f"Custom previewer command timed out after {exc.timeout} seconds"
            )
            if previewer.get("on_nonzero_exit", "details") == "details":
                self._current_content = msg
                self.mount_special_messages(mime=True)
            else:
                self.notify(
                    msg,
                    title=f"Custom Previewer: {name}",
                    severity="error",
                    markup=False,
                )
                self.update_ui(
                    original_path,
                    file_type=previewer.get("on_nonzero_exit", "details"),
                    mime_type=self._mime_type,
                )
            path_utils.dump_exc(self, exc)
        finally:
            if previewer["type"] != "pdf":
                self._current_file_path = original_path
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            if output_path != temp_path and output_path != output:
                with contextlib.suppress(OSError):
                    os.unlink(output_path)

    def show_custom_text_preview(self, output: Text) -> None:
        lines = list(output.split("\n", allow_blank=True))
        if text_preview := self.get_child(WindowedTextPreview):
            self.call_from_thread(
                text_preview.update_preview, lines, language=None, line_numbers=False
            )
            self.call_from_thread(text_preview.set_classes, "text_preview")
        else:
            self.call_from_thread(self.remove_children)
            self.call_from_thread(
                lambda: self.mount(
                    WindowedTextPreview(lines, classes="text_preview").data_bind(
                        type(self.app).ansi_color
                    )
                ),
            )

    def mount_special_messages(self, mime: bool = True) -> None:
        """Mount special messages. Runs in a thread."""
        utils.check_cancel()
        self.log(self._mime_type)
        assert isinstance(self._current_content, str)
        self.set_border(
            "title",
            "Preview" + (f" ({self._mime_type.method})" if self._mime_type else ""),
        )

        display_content: str = self._current_content + "\n"
        if mime and self._mime_type:
            display_content += f"MIME Type: {self._mime_type.mime_type}"
            if (
                config["plugins"]["file_one"]["enabled"]
                and config["plugins"]["file_one"]["get_description"]
            ):
                try:
                    executable = file_one()
                    if executable:
                        process = subprocess.run(
                            [executable, "--brief", "--", self._current_file_path],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=1,
                        )
                        display_content += f"\n{process.stdout.strip()}"
                except subprocess.TimeoutExpired:
                    pass
                except (subprocess.SubprocessError, FileNotFoundError) as exc:
                    path_utils.dump_exc(self, exc)

        display_content = display_content.strip()
        content = display_content if mime else Content(display_content)
        if static_widget := self.get_child(Static):
            self.call_from_thread(static_widget.update, content)
            self.call_from_thread(static_widget.set_classes, "special")
        else:
            self.call_from_thread(self.remove_children)
            utils.check_cancel()
            static_widget = Static(content, classes="special", markup=False)
            self.call_from_thread(self.mount, static_widget)
        # not wasting an isinstance on this
        cast(Static, static_widget).can_focus = True

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Handle mouse scroll up for PDF navigation."""
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            self.update_current_pdf_page_by_diff(-1)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Handle mouse scroll down for PDF navigation."""
        if self.border_title == titles.pdf and self._file_type == "pdf":
            event.stop()
            self.update_current_pdf_page_by_diff(1)

    @property
    def region(self) -> Region:
        if self.loading:
            return self._render_widget.region
        return super().region

    @work(thread=True, exclusive=True, group="preview-resizer")
    @on(events.Resize)
    def _trigger_resize_update(self) -> None:
        """Trigger resize update from a thread."""
        context_token = self.preview_token.set(self._active_preview_token)
        try:
            if self.get_child(WindowedTextPreview):
                return
            if self.border_title in (
                titles.file,
                titles.bat,
            ):
                if config["plugins"]["bat"]["enabled"] and self.show_bat_file_preview():
                    return
                self.show_normal_file_preview()
        except utils.ExitNow:
            pass
        except Exception:
            pass
        finally:
            self.preview_token.reset(context_token)

    @on(events.Show)
    def when_become_visible(self) -> None:
        if isinstance(self._pending_preview_args, tuple):
            pending = self._pending_preview_args
            self._pending_preview_args = None
            self.show_preview(pending[0], pending[1])

    def on_click(self, event: events.Click) -> None:
        if event.widget is self and self.children:
            self.children[-1].focus()

    def show_video_preview(self, source: str, position: int) -> None:
        settings = config["plugins"]["ffmpeg"]
        self.set_border("title", "Video Preview")
        if not settings["enabled"]:
            self._current_content = "Video previews are disabled."
            self.mount_special_messages()
            return

        if position == 0 and self._video_duration is None:
            with contextlib.suppress(OSError, ValueError, subprocess.SubprocessError):
                result = subprocess.run(
                    [settings["ffprobe_path"], "-show_entries", "format=duration", "-v"]
                    + ["error", "-of", "default=noprint_wrappers=1:nokey=1", source],
                    capture_output=True,
                    timeout=3,
                    check=True,
                )
                duration = float(result.stdout)
                if 0 < duration < float("inf"):
                    self.call_from_thread(setattr, self, "_video_duration", duration)

        width, height = settings["size"]
        utils.check_cancel()
        with contextlib.ExitStack() as stack:
            try:
                stdout = stack.enter_context(NamedTemporaryFile(suffix=".png"))
                stderr = stack.enter_context(NamedTemporaryFile(suffix=".log"))
                proc = subprocess.Popen(
                    [settings["ffmpeg_path"], "-v", "error", "-nostdin"]
                    + ["-ss", str(position), "-i", source]
                    + ["-map", "0:v:0", "-frames:v", "1", "-vf"]
                    + [f"scale={width}:{height}:force_original_aspect_ratio=decrease"]
                    + ["-c:v", "png", "-f", "image2pipe", "pipe:1"],
                    stdout=stdout,
                    stderr=stderr,
                )
                seek_read = lambda obj: (obj.seek(0), obj.read())[0]
                timeout, start = 15, monotonic()
                while proc.poll() is None:
                    if monotonic() - start > timeout or utils.check_cancel(False):
                        proc.kill(), proc.communicate()
                        out, err = seek_read(stdout), seek_read(stderr)
                        raise subprocess.TimeoutExpired(proc.args, timeout, out, err)
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        # perfectly reasonable to do this because wait can exit
                        # unlike sleep, so we can check for cancel
                        proc.wait(timeout=0.5)
                proc.communicate()
                if proc.returncode != 0:
                    out, err = seek_read(stdout), seek_read(stderr)
                    raise subprocess.CalledProcessError(
                        proc.returncode, proc.args, output=out, stderr=err
                    )
                stdout.seek(0)
                image = stack.enter_context(Image.open(stdout)).copy()
            except (
                OSError,
                ValueError,
                subprocess.SubprocessError,
                subprocess.TimeoutExpired,
            ) as exc:
                utils.check_cancel()
                self._current_content = f"Cannot preview video:\n{exc!r}"
                self.mount_special_messages()
                return

        if widget := self.get_child(".image_preview"):
            self.call_from_thread(setattr, widget, "image", image)
        else:
            self.call_from_thread(self.remove_children)
            widget = self.NewImage(image)
            widget.can_focus = True
            self.call_from_thread(self.mount, widget)
        self.set_border("subtitle", f"{position // 60:02}:{position % 60:02}")

    def _seek_video(self, delta: int) -> None:
        if not config["plugins"]["ffmpeg"]["enabled"] or self._video_source is None:
            return
        position = max(0, self._video_position + delta)
        if self._video_duration is not None:
            position = min(position, ceil(self._video_duration) - 1)
        if position != self._video_position:
            self._video_position = position
            self._rendered_preview_key = None
            self.show_preview(*self._video_source)

    def _is_pdf(self) -> bool:
        return (
            self._file_type == "pdf"
            or config["settings"]
            .get("previewers", {})
            .get(self._file_type, {})
            .get("type")
            == "pdf"
        )

    def action_up(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(-1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_up(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_up(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_cursor_up()

    def action_down(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_down(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_down(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_cursor_down()

    def action_left(self) -> None:
        if self._file_type == "video":
            return self._seek_video(-config["plugins"]["ffmpeg"]["seek_seconds"])
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(-1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_left(animate=False)

    def action_right(self) -> None:
        if self._file_type == "video":
            return self._seek_video(config["plugins"]["ffmpeg"]["seek_seconds"])
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_right(animate=False)

    def action_page_up(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(-1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_page_up(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_page_up(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_page_up()

    def action_page_down(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_page_down(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_page_down(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_page_down()

    def action_page_left(self) -> None:
        if self._file_type == "video":
            return self._seek_video(-config["plugins"]["ffmpeg"]["page_seek_seconds"])
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(-1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_page_left(animate=False)

    def action_page_right(self) -> None:
        if self._file_type == "video":
            return self._seek_video(config["plugins"]["ffmpeg"]["page_seek_seconds"])
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page_by_diff(1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_page_right(animate=False)

    def action_home(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page(0)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_home(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_home(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_home()

    def action_end(self) -> None:
        if self._is_pdf() and self.pdf.images is not None:
            self.update_current_pdf_page(self.pdf.total_pages - 1)
        elif text_preview := self.get_child(WindowedTextPreview):
            text_preview.scroll_end(animate=False)
        elif self.border_title == titles.archive and (
            filelist := self.get_child(FileList)
        ):
            filelist.scroll_end(animate=False)
        elif self.border_title == titles.folder and (
            filelist := self.get_child(FileList)
        ):
            filelist.action_end()

    def _sync_mime(
        self, file_path: str, mime_type: preview_utils.MimeResult | None = None
    ) -> None:
        mime_str = mime_type.mime_type if mime_type else "--"
        with contextlib.suppress(NoMatches):
            metadata_container = self.app.query_one("MetadataContainer")
            option = metadata_container._current_option
            if (
                isinstance(option, FileListSelectionWidget)
                and option.dir_entry.path == file_path
            ):
                option.mime_type = mime_str
                with contextlib.suppress(NoMatches):
                    metadata_container.query_one("#metadata-mime", Static).update(
                        mime_str or "--"
                    )
