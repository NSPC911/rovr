from rovr.app import Application


async def test_run() -> None:
    app = Application()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("?")
        assert True
