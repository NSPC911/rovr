from rich.errors import StyleSyntaxError
from rich.style import Style
from textual.color import Color, ColorParseError
from textual.validation import ValidationResult, Validator


class ColorValidator(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        try:
            Color.parse(value)
            return self.success()
        except ColorParseError as exc:
            self.failure_description = exc.__str__()
            return self.failure()


class LayoutValidator(Validator):
    def __init__(self) -> None:
        super().__init__(failure_description="Needs to be one of `vertical`, `horizontal` or `grid`")

    def validate(self, value: str) -> ValidationResult:
        if value in ["vertical", "horizontal", "grid"]:
            return self.success()
        else:
            return self.failure()

class StyleValidator(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        try:
            Style.parse(value)
            return self.success()
        except StyleSyntaxError as exc:
            self.failure_description = exc.__str__()
            return self.failure()
