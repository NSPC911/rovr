from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import tempfile
from io import BytesIO

from PIL import Image
from PIL.Image import Image as PILImage

from rovr.functions.command import run_command_async

# Keys whose values should be parsed as integers from pdfinfo output
pdfinfo_turn_to_int = {"Pages"}


async def _run_commands(
    commands: list[list[str]],
    env: dict[str, str],
    startupinfo: subprocess.STARTUPINFO | None,
) -> list[subprocess.CompletedProcess[bytes]]:
    tasks: list[asyncio.Task[subprocess.CompletedProcess[bytes]]] = []
    async with asyncio.TaskGroup() as group:
        tasks.extend(
            group.create_task(
                run_command_async(
                    command,
                    env=env,
                    startupinfo=startupinfo,
                    timeout=15,
                )
            )
            for command in commands
        )
    return [task.result() for task in tasks]


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


async def get_pdf_info(
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
    """
    command = [_get_command_path("pdfinfo", poppler_path), pdf_path]

    completed = await run_command_async(
        command,
        env=_get_env(poppler_path),
        startupinfo=_get_startupinfo(),
        timeout=5,
    )
    out, err = completed.stdout, completed.stderr

    if completed.returncode != 0:
        raise ValueError(
            f"pdfinfo failed with error code {completed.returncode}.\n{err.decode('utf8', 'ignore')}"
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


async def get_pdf_images(
    pdf_path: str,
    first_page: int = 1,
    last_page: int | None = None,
    poppler_path: str | None = None,
    use_pdftocairo: bool = False,
    thread_count: int = 1,
) -> list[PILImage]:
    """Render PDF pages as PIL images using poppler's `pdftoppm` or `pdftocairo`.
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
        return await _render_with_pdftocairo(
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
        return await _render_with_pdftoppm(
            pdf_path=pdf_path,
            first_page=first_page,
            last_page=last_page,
            page_count=page_count,
            poppler_path=poppler_path,
            thread_count=thread_count,
            env=env,
            startupinfo=startupinfo,
        )


async def _render_with_pdftoppm(
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

    """
    command_base = _get_command_path("pdftoppm", poppler_path)

    if page_count is None or thread_count <= 1:
        # Single process: render all requested pages at once
        args = [command_base, "-r", "200"]
        args.extend(["-f", str(first_page)])
        if last_page is not None:
            args.extend(["-l", str(last_page)])
        args.append(pdf_path)

        completed = await run_command_async(
            args, env=env, startupinfo=startupinfo, timeout=15
        )
        return await asyncio.to_thread(_parse_ppm_buffer, completed.stdout)

    # Multi-process: split page ranges across subprocesses
    remainder = page_count % thread_count
    current_page = first_page
    commands: list[list[str]] = []

    for _ in range(thread_count):
        chunk = page_count // thread_count + int(remainder > 0)
        chunk_last = current_page + chunk - 1

        args = [command_base, "-r", "200"]
        args.extend(["-f", str(current_page)])
        args.extend(["-l", str(chunk_last)])
        args.append(pdf_path)

        commands.append(args)

        current_page += chunk
        remainder -= int(remainder > 0)

    completed_commands = await _run_commands(commands, env, startupinfo)
    chunks = await asyncio.gather(
        *(
            asyncio.to_thread(_parse_ppm_buffer, completed.stdout)
            for completed in completed_commands
        )
    )
    return [image for chunk in chunks for image in chunk]


async def _render_with_pdftocairo(
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

            await run_command_async(args, env=env, startupinfo=startupinfo, timeout=15)
            return await asyncio.to_thread(
                _load_images_from_folder, output_folder, prefix, "png"
            )

        # multi proc stuff
        remainder = page_count % thread_count
        current_page = first_page
        commands: list[tuple[str, list[str]]] = []

        for i in range(thread_count):
            chunk = page_count // thread_count + int(remainder > 0)
            chunk_last = current_page + chunk - 1
            prefix = f"chunk{i}"

            args = [command_base, "-png", "-r", "200"]
            args.extend(["-f", str(current_page)])
            args.extend(["-l", str(chunk_last)])
            args.extend([pdf_path, os.path.join(output_folder, prefix)])

            commands.append((prefix, args))

            current_page += chunk
            remainder -= int(remainder > 0)

        await _run_commands([args for _, args in commands], env, startupinfo)
        chunks = await asyncio.gather(
            *(
                asyncio.to_thread(
                    _load_images_from_folder, output_folder, prefix, "png"
                )
                for prefix, _ in commands
            )
        )
        return [image for chunk in chunks for image in chunk]
    finally:
        shutil.rmtree(output_folder, ignore_errors=True)
