from __future__ import annotations

import asyncio
import json
import os
import stat
from contextlib import suppress
from pathlib import Path
from typing import Literal, TypedDict

from rovr.variables.maps import RovrVars

IPC_DIRECTORY = Path(RovrVars.ROVRTEMP) / "ipc"


class Instance(TypedDict):
    pid: int
    port: int
    token: str


class InstanceInfo(TypedDict):
    pid: int
    status: Literal["running", "unresponsive"]


def _ensure_directory() -> None:
    # more safety
    IPC_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    IPC_DIRECTORY.chmod(0o700)


def publish_instance(port: int, token: str) -> Path:
    _ensure_directory()
    descriptor = Instance({
        "pid": os.getpid(),
        "port": port,
        "token": token,
    })
    destination = IPC_DIRECTORY / f"{descriptor['pid']}.json"
    temporary = IPC_DIRECTORY / f".{descriptor['pid']}-{token}.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(descriptor, file)
        os.replace(temporary, destination)
        # safety first
        destination.chmod(0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def unpublish_instance(descriptor: Path, token: str) -> None:
    try:
        current = json.loads(descriptor.read_text(encoding="utf-8"))
        if current.get("token") == token:
            descriptor.unlink(missing_ok=True)
    except (OSError, ValueError, AttributeError):
        pass


def _read_descriptor(path: Path) -> Instance | None:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or (
            os.name != "nt" and metadata.st_mode & 0o077
        ):
            return
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            return
        descriptor: dict | Instance = json.loads(path.read_text(encoding="utf-8"))
        pid = descriptor["pid"]
        port = descriptor["port"]
        token = descriptor["token"]
        # checking if tampering happened basically
        if (
            not isinstance(pid, int)
            or isinstance(pid, bool)
            or pid <= 0
            or not isinstance(port, int)
            or isinstance(port, bool)
            or not 0 < port < 65536
            or not isinstance(token, str)
            or not token
            or path.name != f"{pid}.json"
        ):
            return
        return Instance({"pid": pid, "port": port, "token": token})
    except (OSError, ValueError, KeyError, TypeError):
        return


def instance_for_pid(pid: int) -> Instance | None:
    return _read_descriptor(IPC_DIRECTORY / f"{pid}.json")


async def _probe_instance(path: Path, descriptor: Instance) -> InstanceInfo | None:
    info = InstanceInfo({
        "pid": descriptor["pid"],
        "status": "unresponsive",
    })
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", descriptor["port"]), 1
        )
    except TimeoutError:
        return info
    except ConnectionRefusedError:
        path.unlink(missing_ok=True)
        return
    except OSError:
        return info

    try:
        writer.write(
            json.dumps({
                "token": descriptor["token"],
                "action": "_show_urself",
                "args": [],
            }).encode()
            + b"\n"
        )
        await writer.drain()
        data = await asyncio.wait_for(reader.readline(), 1)
        response = json.loads(data.decode())
        if (
            isinstance(response, dict)
            and response.get("ok") is True
            and response.get("out")
            == {"pid": descriptor["pid"], "port": descriptor["port"]}
        ):
            info["status"] = "running"
            return info
    except (TimeoutError, OSError):
        return info
    except (UnicodeDecodeError, ValueError, TypeError):
        pass
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()

    with suppress(OSError):
        path.unlink(missing_ok=True)


async def discover_instances() -> list[InstanceInfo]:
    try:
        paths = list(IPC_DIRECTORY.glob("*.json"))
    except OSError:
        return []

    probes = []
    for path in paths:
        descriptor = _read_descriptor(path)
        if descriptor is None:
            with suppress(OSError):
                path.unlink(missing_ok=True)
        else:
            probes.append(_probe_instance(path, descriptor))
    instances = await asyncio.gather(*probes)
    return sorted(
        (instance for instance in instances if instance is not None),
        key=lambda instance: instance["pid"],
    )
