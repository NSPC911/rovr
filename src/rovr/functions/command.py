from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import suppress
from os import PathLike
from shlex import join as shell_join
from shlex import split as shell_split
from typing import Any


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    with suppress(ProcessLookupError):
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=0.5)
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await process.wait()


async def run_command_async(
    command: str | Sequence[str | PathLike[str]],
    *,
    shell: bool = False,
    timeout: float | None = None,
    stdin: int | None = subprocess.DEVNULL,
    env: Mapping[str, str] | None = None,
    startupinfo: subprocess.STARTUPINFO | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[bytes]:
    if shell:
        if not isinstance(command, str):
            command = shell_join([str(part) for part in command])
        process = await asyncio.create_subprocess_shell(
            command,
            stdin=stdin,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            startupinfo=startupinfo,
            **kwargs,
        )
    else:
        if isinstance(command, str):
            command = shell_split(command)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=stdin,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            startupinfo=startupinfo,
            **kwargs,
        )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except BaseException:
        await _stop_process(process)
        raise
    return subprocess.CompletedProcess(command, process.returncode or 0, stdout, stderr)
