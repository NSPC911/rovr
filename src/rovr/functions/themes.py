from textual.color import Color

from rovr.classes.theme import RovrThemeClass
from rovr.variables.constants import config


def get_custom_themes() -> list:
    """
    Get the custom themes defined in the config file.

    Returns:
        list: A list of custom themes.
    """
    custom_themes = []
    for theme in config["custom_theme"]:
        if bar_gradient := theme.get("bar_gradient"):
            if "default" in bar_gradient["default"]:
                for color in bar_gradient["default"]:
                    Color.parse(color)
            if "error" in bar_gradient["error"]:
                for color in bar_gradient["error"]:
                    Color.parse(color)
        custom_themes.append(
            RovrThemeClass(
                bar_gradient=theme.get("bar_gradient", {}),
                name=theme["name"]
                .lower()
                .replace(" ", "-"),  # Keep it similar to default textual behaviour
                primary=theme["primary"],
                secondary=theme["secondary"],
                accent=theme["accent"],
                foreground=theme["foreground"],
                background=theme["background"],
                success=theme["success"],
                warning=theme["warning"],
                error=theme["error"],
                surface=theme["surface"],
                panel=theme["panel"],
                dark=theme["is_dark"],
                variables=theme.get("variables", {}),
            )
        )
    return custom_themes
