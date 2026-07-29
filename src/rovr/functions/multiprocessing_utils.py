from __future__ import annotations

import os
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing.process import BaseProcess

_safe_path_lock = threading.Lock()
_safe_path_users = 0
_previous_safe_path: str | None = None


def _enable_safe_path() -> None:
    global _previous_safe_path, _safe_path_users

    with _safe_path_lock:
        if _safe_path_users == 0:
            _previous_safe_path = os.environ.get("PYTHONSAFEPATH")
            os.environ["PYTHONSAFEPATH"] = "1"
        _safe_path_users += 1


def _disable_safe_path() -> None:
    global _previous_safe_path, _safe_path_users

    with _safe_path_lock:
        _safe_path_users -= 1
        if _safe_path_users != 0:
            return
        if _previous_safe_path is None:
            os.environ.pop("PYTHONSAFEPATH", None)
        else:
            os.environ["PYTHONSAFEPATH"] = _previous_safe_path
        _previous_safe_path = None


def start_process(process: BaseProcess) -> None:
    _enable_safe_path()
    try:
        process.start()
    finally:
        _disable_safe_path()


class SafePathProcessPoolExecutor(ProcessPoolExecutor):
    def __init__(self, max_workers: int) -> None:
        _enable_safe_path()
        self._safe_path_enabled = True
        try:
            super().__init__(max_workers=max_workers)
        except Exception:
            self._disable_safe_path()
            raise

    def _disable_safe_path(self) -> None:
        if self._safe_path_enabled:
            self._safe_path_enabled = False
            _disable_safe_path()

    def shutdown(
        self,
        wait: bool = True,
        *,
        cancel_futures: bool = False,
    ) -> None:
        try:
            super().shutdown(wait=wait, cancel_futures=cancel_futures)
        finally:
            self._disable_safe_path()
