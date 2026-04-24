import asyncio

if hasattr(asyncio, "windows_utils"):
    import asyncio.windows_utils

    def fileno(self):  # noqa: ANN202, ANN001
        if self._handle is None:
            return -1
        return self._handle

    asyncio.windows_utils.PipeHandle.fileno = fileno  # ty: ignore[invalid-assignment]
