from textual.widgets import Button

from rovr.functions.icons import get_icon
from rovr.functions.path import decompress
from rovr.screens import YesOrNo
from rovr.variables.constants import config


class PasteButton(Button):
    ALLOW_MAXIMIZE = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            get_icon("general", "paste")[0],
            classes="option",
            id="paste",
            *args,
            **kwargs,
        )

    def on_mount(self) -> None:
        if config["interface"]["tooltips"]:
            self.tooltip = "Paste files from clipboard"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.disabled:
            return
        """Paste files from clipboard"""
        selected_items = self.app.query_one(
            "Clipboard"
        ).selected  # dont include highlighted
        if selected_items:
            # decompress items
            selected_items = [decompress(item) for item in selected_items]
            # split into two items, those ending with `-cut` and those ending with `-copy`
            to_copy, to_cut = (
                [item[:-5] for item in selected_items if item.endswith("-copy")],
                [item[:-4] for item in selected_items if item.endswith("-cut")],
            )

            async def callback(response: str) -> None:
                """Callback to paste files after confirmation"""
                if response:
                    self.app.query_one("ProcessContainer").paste_items(to_copy, to_cut)

            self.app.push_screen(
                YesOrNo(
                    message="Are you sure you want to "
                    + (
                        f"copy {len(to_copy)} item{'s' if len(to_copy) != 1 else ''}{' and ' if len(to_cut) != 0 else ''}"
                        if len(to_copy) > 0
                        else ""
                    )
                    + (
                        f"cut {len(to_cut)} item{'s' if len(to_cut) != 1 else ''}"
                        if len(to_cut) > 0
                        else ""
                    )
                    + "?"
                ),
                callback=callback,
            )
