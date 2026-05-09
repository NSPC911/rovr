from dataclasses import dataclass, field

from textual.theme import Theme

from .config import _RovrConfigCustomThemeItemBarGradient


@dataclass
class RovrThemeClass(Theme):
    name: str
    primary: str
    secondary: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    foreground: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    boost: str | None = None
    dark: bool = True
    luminosity_spread: float = 0.15
    text_alpha: float = 0.95
    variables: dict[str, str] = field(default_factory=dict)
    bar_gradient: _RovrConfigCustomThemeItemBarGradient | None = None
