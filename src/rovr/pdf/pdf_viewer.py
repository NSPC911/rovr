from pathlib import Path

import fitz
import textual_image.widget as timg
from PIL import Image as PILImage
from pymupdf import EmptyFileError, FileDataError
from textual import events
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual_image.widget import Image

from rovr.pdf.exceptions import NotAPDFError, PDFHasAPasswordError, PDFRuntimeError
from rovr.variables.constants import config


class PDFViewer(ScrollableContainer):
    """A PDF viewer widget."""

    DEFAULT_CSS = """
    PDFViewer {
        height: 1fr;
        width: 1fr;
        Image {
            width: auto;
            height: auto;
            align: center bottom;
        }
    }
    """

    protocol: reactive[str] = reactive("Auto")
    """Protocol to use ["Auto", "TGP", "Sixel", "Halfcell", "Unicode"]"""

    def __init__(
        self,
        path: str | Path,
        protocol: str = "",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the PDFViewer widget

        Args:
            path(str): Path to a PDF file.
            protocol(str): The protocol to use (leave empty or 'Auto' to use auto protocol)
            name(str): The name of this widget.
            id(str): The ID of the widget in the DOM.
            classes(str): The CSS classes for this widget.

        Raises:
            PDFHasAPasswordError: When the PDF file is password protected
            NotAPDFError: When the file is not a valid PDF
        """  # noqa: DOC502 (explicitly raises them while checking)
        super().__init__(name=name, id=id, classes=classes, disabled=False)
        assert protocol in ["Auto", "TGP", "Sixel", "Halfcell", "Unicode", ""]
        self._doc: fitz.Document | None = None
        self._total_pages: int = 0
        self.protocol = protocol
        self._path = path
        self._current_page = 0

        # Pre-check if the PDF is valid and not password protected
        self._check_pdf_file(path)

        # bindings
        self.up_page = config["keybinds"]["up"] + config["keybinds"]["page_up"]
        self.down_page = config["keybinds"]["down"] + config["keybinds"]["page_down"]

    def _check_pdf_file(self, path: str | Path) -> None:
        """Check if the PDF file is valid and not password protected

        Args:
            path: Path to the PDF file

        Raises:
            NotAPDFError: When the file is not a valid PDF
            PDFHasAPasswordError: When the PDF file is password protected
        """  # noqa: DOC502 (explicitly raises them)
        try:
            # Try to open the document
            doc = fitz.open(path)

            # Check if the document is encrypted and requires a password
            if doc.is_encrypted and doc.needs_pass:
                doc.close()
                raise PDFHasAPasswordError(
                    f"{path} is a document that is encrypted, and cannot be read."
                )

            # Close the document as we'll reopen it during on_mount
            doc.close()
        except (FileDataError, EmptyFileError):
            # Not a valid PDF
            raise NotAPDFError(f"{path} does not point to a valid PDF file")

    def _open_document(self) -> None:
        """Open the PDF document and store it for reuse.

        Raises:
            NotAPDFError: When the pdf is not accurate at all
        """  # noqa: DOC502
        # Close existing document if any
        if self._doc:
            self._doc.close()
            self._doc = None

        try:
            self._doc = fitz.open(self.path)
            self._total_pages = self._doc.page_count
        except (FileDataError, EmptyFileError):
            raise NotAPDFError(f"{self.path} does not point to a valid PDF file")

    def on_mount(self) -> None:
        """Load the PDF when the widget is mounted."""
        self.can_focus = True

    @property
    def total_pages(self) -> int:
        """The total number of pages in the currently open file"""
        return self._total_pages

    def compose(self) -> ComposeResult:
        yield timg.__dict__[
            self.protocol + "Image" if self.protocol != "Auto" else "Image"
        ](PILImage.new("RGB", (self.size.width, self.size.height)), id="pdf-image")

    def _render_current_page_pil(self) -> PILImage.Image:
        """Renders the current page and returns a PIL image.
        Returns:
            PIL.Image: a valid PIL image

        Raises:
            PDFRuntimeError: when a document isn't opened before this function was called, by any means
            PDFHasAPasswordError: when the document has a password
        """  # noqa: DOC502 (explicitly raises them, not sure why it's annoyed)
        if not self._doc:
            raise PDFRuntimeError("Document not opened. Call _open_document() first.")

        try:
            page = self._doc.load_page(self.current_page)
            pix = page.get_pixmap()
            mode = "RGBA" if pix.alpha else "RGB"
            image = PILImage.frombytes(mode, (pix.width, pix.height), pix.samples)
            return image
        except ValueError:
            # Preserve the original exception traceback to make it catchable
            raise PDFHasAPasswordError(
                f"{self.path} is a document that is encrypted, and cannot be read."
            )

    def render_page(self) -> None:
        """Renders the current page and updates the image widget.
        Raises:
            PDFRuntimeError: when a document isn't opened before this function was called, by any means
        """  # noqa: DOC502 (implicitly raises PDF Runtime Error from self._render_current_page)
        image_widget: Image = self.query_one("#pdf-image")  # type: ignore
        image_widget.image = self._render_current_page_pil()

    def watch_protocol(self, protocol: str) -> None:
        """Change the rendering protocol
        Args:
            protocol(str): The protocol to use
        Raises:
            AssertionError: When the protocol isn't `Auto`, `TGP`, `Sixel`, `Halfcell`, `Unicode` ir `<empty>` (auto)"""
        assert protocol in ["Auto", "TGP", "Sixel", "Halfcell", "Unicode", ""]
        if self.is_mounted:
            self.refresh(recompose=True)
            self.render_page()

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, file_path: str) -> None:
        if not self.is_mounted:
            return

        self._check_pdf_file(file_path)

        # Reopen the document with the new path
        self._open_document()
        self._current_page = 0
        self.render_page()
        self._path = file_path

    @property
    def current_page(self) -> int:
        return self._current_page

    @current_page.setter
    def current_page(self, new_page: int) -> None:
        """Change the current page to a different page based on the value provided
        Args:
            new_page(int): The page to switch to.
        """
        self.render_page()

    def next_page(self) -> None:
        """Go to the next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1

    def previous_page(self) -> None:
        """Go to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1

    def go_to_start(self) -> None:
        """Go to the first page."""
        self.current_page = 0

    def go_to_end(self) -> None:
        """Go to the last page."""
        self.current_page = self.total_pages - 1

    def on_unmount(self) -> None:
        """Close any open document when the widget is unmounted."""
        if self._doc:
            self._doc.close()
            self._doc = None

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.previous_page()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.next_page()

    def on_key(self, event: events.Key) -> None:
        if event.key in self.up_page:
            self.previous_page()
        if event.key in self.down_page:
            self.next_page()
        if event.key in config["keybinds"]["home"]:
            self.go_to_start()
        if event.key in config["keybinds"]["end"]:
            self.go_to_end
