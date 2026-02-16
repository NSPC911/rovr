import os
import platform
import shutil
import subprocess
import tempfile
from io import BytesIO
from subprocess import PIPE, Popen, TimeoutExpired

from PIL import Image
from PIL.Image import Image as PILImage

# Keys whose values should be parsed as integers from pdfinfo output
pdfinfo_turn_to_int = {"Pages"}


def _get_command_path(command: str, poppler_path: str | None = None) -> str:
    """Build the full path to a poppler binary.
    Args:
        command: The poppler binary name (e.g. "pdfinfo", "pdftoppm")
        poppler_path: Optional directory containing poppler binaries

    Returns:
        The full path to the command
    """
    if platform.system() == "Windows":
        command = command + ".exe"

    if poppler_path is not None:
        command = os.path.join(poppler_path, command)

    return command


def _get_startupinfo() -> subprocess.STARTUPINFO | None:
    """Get STARTUPINFO to suppress console windows on Windows.
    Returns:
        STARTUPINFO with STARTF_USESHOWWINDOW on Windows, None otherwise
    """
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None


def _get_env(poppler_path: str | None = None) -> dict[str, str]:
    """Build environment dict with LD_LIBRARY_PATH for poppler on Linux.
    Args:
        poppler_path: Optional directory containing poppler binaries

    Returns:
        Copy of os.environ with LD_LIBRARY_PATH prepended if needed
    """
    env = os.environ.copy()
    if poppler_path is not None:
        env["LD_LIBRARY_PATH"] = poppler_path + ":" + env.get("LD_LIBRARY_PATH", "")
    return env


def _parse_ppm_buffer(data: bytes) -> list[PILImage]:
    """Parse concatenated PPM images from pdftoppm stdout.

    PPM files have a header of: magic number, dimensions, max color value,
    each separated by newlines, followed by raw pixel data.

    Args:
        data: Raw bytes from pdftoppm stdout

    Returns:
        list[PILImage]: list parsed from the PPM stream

    Raises:
        ValueError: If the expected PPM format is not found in data
    """
    images: list[PILImage] = []
    index = 0

    if not data:
        return images

    while index < len(data):
        if data[index : index + 2] != b"P6":
            raise ValueError(
                f"Expected PPM magic 'P6' at offset {index}, got {repr(data[index : index + 10])}"
            )
        # PPM header: P6\n<width> <height>\n<maxval>\n<pixel data>
        header_parts = data[index : index + 40].split(b"\n")[0:3]
        code, size, rgb = header_parts[0], header_parts[1], header_parts[2]
        size_x, size_y = size.split(b" ")
        file_size = len(code) + len(size) + len(rgb) + 3 + int(size_x) * int(size_y) * 3
        images.append(Image.open(BytesIO(data[index : index + file_size])))
        index += file_size

    return images


def _load_images_from_folder(
    output_folder: str, output_prefix: str, extension: str
) -> list[PILImage]:
    """Load rendered images from a temp folder (used with pdftocairo).
    Args:
        output_folder: Directory containing rendered image files
        output_prefix: Filename prefix used for rendered files
        extension: File extension to match (e.g. "png")

    Returns:
        list[PILImage]: list loaded from matching files, sorted by name
    """
    images: list[PILImage] = []
    for filename in sorted(os.listdir(output_folder)):
        if filename.startswith(output_prefix) and filename.endswith(f".{extension}"):
            with Image.open(os.path.join(output_folder, filename)) as img:
                img.load()
                images.append(img)
    return images


def get_pdf_info(
    pdf_path: str,
    poppler_path: str | None = None,
) -> dict[str, str | int]:
    """Get PDF metadata
    Args:
        pdf_path: Path to the PDF file
        poppler_path: Optional directory containing poppler binaries

    Returns:
        dict: metadata info with int values parsed as integers, rest as strings

    Raises:
        ValueError: Page count cannot be determined from output.
        TimeoutExpired: If the pdfinfo command takes too long to execute.
    """
    command = [_get_command_path("pdfinfo", poppler_path), pdf_path]

    proc = Popen(
        command,
        env=_get_env(poppler_path),
        stdout=PIPE,
        stderr=PIPE,
        startupinfo=_get_startupinfo(),
    )
    try:
        out, err = proc.communicate(timeout=5)
    except TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise

    if proc.returncode != 0:
        raise ValueError(
            f"pdfinfo failed with error code {proc.returncode}.\n{err.decode('utf8', 'ignore')}"
        )

    result: dict[str, str | int] = {}
    for field in out.decode("utf8", "ignore").split("\n"):
        split_field = field.split(":")
        key = split_field[0]
        value = ":".join(split_field[1:])
        if key != "":
            result[key] = (
                int(value.strip()) if key in pdfinfo_turn_to_int else value.strip()
            )

    if "Pages" not in result:
        raise ValueError(f"Unable to get page count.\n{err.decode('utf8', 'ignore')}")

    return result


def get_pdf_images(
    pdf_path: str,
    first_page: int = 1,
    last_page: int | None = None,
    poppler_path: str | None = None,
    use_pdftocairo: bool = False,
    thread_count: int = 1,
) -> list[PILImage]:
    """Render PDF pages as PIL images using poppler's ``pdftoppm`` or ``pdftocairo``.
    Args:
        pdf_path: Path to the PDF file
        first_page: First page to render (1-indexed)
        last_page: Last page to render (1-indexed, inclusive). If None,
            renders through the last page.
        poppler_path: Optional directory containing poppler binaries
        use_pdftocairo: Use pdftocairo instead of pdftoppm (render to ppm from stdout vs png files in temp folder)
        thread_count: Number of parallel subprocess invocations

    Returns:
        List of PIL images, one per rendered page
    """
    if last_page is not None and first_page > last_page:
        return []

    page_count = (last_page - first_page + 1) if last_page is not None else None

    if thread_count < 1:
        thread_count = 1

    if page_count is not None and thread_count > page_count:
        thread_count = page_count

    env = _get_env(poppler_path)
    startupinfo = _get_startupinfo()

    if use_pdftocairo:
        return _render_with_pdftocairo(
            pdf_path=pdf_path,
            first_page=first_page,
            last_page=last_page,
            page_count=page_count,
            poppler_path=poppler_path,
            thread_count=thread_count,
            env=env,
            startupinfo=startupinfo,
        )
    else:
        return _render_with_pdftoppm(
            pdf_path=pdf_path,
            first_page=first_page,
            last_page=last_page,
            page_count=page_count,
            poppler_path=poppler_path,
            thread_count=thread_count,
            env=env,
            startupinfo=startupinfo,
        )


def _render_with_pdftoppm(
    pdf_path: str,
    first_page: int,
    last_page: int | None,
    page_count: int | None,
    poppler_path: str | None,
    thread_count: int,
    env: dict[str, str],
    startupinfo: subprocess.STARTUPINFO | None,
) -> list[PILImage]:
    """Render pages via pdftoppm, reading PPM bytes from stdout.

    Args:
        pdf_path: Path to the PDF file
        first_page: First page (1-indexed)
        last_page: Last page (1-indexed, inclusive) or None
        page_count: Total pages to render, or None if last_page is None
        poppler_path: Optional poppler binary directory
        thread_count: Number of parallel subprocesses
        env: Environment variables dict
        startupinfo: Windows STARTUPINFO or None

    Returns:
        List of PIL images

    Raises:
        TimeoutExpired: If any pdftoppm command takes too long to execute
    """
    command_base = _get_command_path("pdftoppm", poppler_path)

    if page_count is None or thread_count <= 1:
        # Single process: render all requested pages at once
        args = [command_base, "-r", "200"]
        args.extend(["-f", str(first_page)])
        if last_page is not None:
            args.extend(["-l", str(last_page)])
        args.append(pdf_path)

        try:
            proc = Popen(
                args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo
            )
            data, _ = proc.communicate(timeout=15)
        except TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        return _parse_ppm_buffer(data)

    # Multi-process: split page ranges across subprocesses
    remainder = page_count % thread_count
    current_page = first_page
    processes: list[Popen] = []

    for _ in range(thread_count):
        chunk = page_count // thread_count + int(remainder > 0)
        chunk_last = current_page + chunk - 1

        args = [command_base, "-r", "200"]
        args.extend(["-f", str(current_page)])
        args.extend(["-l", str(chunk_last)])
        args.append(pdf_path)

        processes.append(
            Popen(args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo)
        )

        current_page += chunk
        remainder -= int(remainder > 0)

    images: list[PILImage] = []
    saved_exception: TimeoutExpired | None = None
    for proc in processes:
        if saved_exception is not None:
            proc.kill()
            proc.communicate()
            continue
        try:
            data, _ = proc.communicate(timeout=15)
        except TimeoutExpired as exc:
            proc.kill()
            proc.communicate()
            if not saved_exception:
                saved_exception = exc
                continue
        images += _parse_ppm_buffer(data)
    if saved_exception is not None:
        raise saved_exception

    return images


def _render_with_pdftocairo(
    pdf_path: str,
    first_page: int,
    last_page: int | None,
    page_count: int | None,
    poppler_path: str | None,
    thread_count: int,
    env: dict[str, str],
    startupinfo: subprocess.STARTUPINFO | None,
) -> list[PILImage]:
    """Render pages via pdftocairo, writing PNGs to a temp directory.

    Args:
        pdf_path: Path to the PDF file
        first_page: First page (1-indexed)
        last_page: Last page (1-indexed, inclusive) or None
        page_count: Total pages to render, or None if last_page is None
        poppler_path: Optional poppler binary directory
        thread_count: Number of parallel subprocesses
        env: Environment variables dict
        startupinfo: Windows STARTUPINFO or None

    Returns:
        List of PIL images

    Raises:
        TimeoutExpired: If any pdftocairo command takes too long to execute
    """
    command_base = _get_command_path("pdftocairo", poppler_path)
    output_folder = tempfile.mkdtemp()

    try:
        if page_count is None or thread_count <= 1:
            prefix = "page"
            args = [command_base, "-png", "-r", "200"]
            args.extend(["-f", str(first_page)])
            if last_page is not None:
                args.extend(["-l", str(last_page)])
            args.extend([pdf_path, os.path.join(output_folder, prefix)])

            proc = Popen(
                args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo
            )
            try:
                proc.communicate(timeout=15)
            except TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise
            return _load_images_from_folder(output_folder, prefix, "png")

        # multi proc stuff
        remainder = page_count % thread_count
        current_page = first_page
        processes: list[tuple[str, Popen]] = []

        for i in range(thread_count):
            chunk = page_count // thread_count + int(remainder > 0)
            chunk_last = current_page + chunk - 1
            prefix = f"chunk{i}"

            args = [command_base, "-png", "-r", "200"]
            args.extend(["-f", str(current_page)])
            args.extend(["-l", str(chunk_last)])
            args.extend([pdf_path, os.path.join(output_folder, prefix)])

            processes.append((
                prefix,
                Popen(args, env=env, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo),
            ))

            current_page += chunk
            remainder -= int(remainder > 0)

        images: list[PILImage] = []
        saved_exception: TimeoutExpired | None = None
        for prefix, proc in processes:
            if saved_exception is not None:
                proc.kill()
                proc.communicate()
                continue
            try:
                proc.communicate(timeout=15)
            except TimeoutExpired as exc:
                proc.kill()
                proc.communicate()
                if not saved_exception:
                    saved_exception = exc
                    continue
            images += _load_images_from_folder(output_folder, prefix, "png")
        if saved_exception is not None:
            raise saved_exception

        return images
    finally:
        shutil.rmtree(output_folder, ignore_errors=True)
