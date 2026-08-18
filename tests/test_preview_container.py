import asyncio

import pytest
from textual.app import App, ComposeResult

from rovr.core.preview_container import ExitNow, PreviewContainer, preview_token


class PreviewTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield PreviewContainer()


async def test_call_from_thread_rejects_stale_preview() -> None:
    app = PreviewTestApp()

    async with app.run_test():
        preview = app.query_one(PreviewContainer)
        current_token = preview._active_preview_token

        def call_with(token: object) -> int:
            context_token = preview_token.set(token)
            try:
                return preview.call_from_thread(lambda: 42)
            finally:
                preview_token.reset(context_token)

        assert await asyncio.to_thread(call_with, current_token) == 42

        preview._active_preview_token = object()
        with pytest.raises(ExitNow):
            await asyncio.to_thread(call_with, current_token)
