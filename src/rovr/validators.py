from typing import Literal

from rich.errors import StyleSyntaxError
from rich.style import Style
from textual.color import Color, ColorParseError
from textual.css.scalar import Scalar, ScalarParseError
from textual.dom import BadIdentifier, check_identifiers
from textual.geometry import Spacing
from textual.validation import ValidationResult, Validator


class ColorValidator(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        try:
            Color.parse(value)
            return self.success()
        except ColorParseError as exc:
            return self.failure(str(exc))


class LayoutValidator(Validator):
    def __init__(self) -> None:
        super().__init__(
            failure_description="Needs to be one of `vertical`, `horizontal` or `grid`"
        )

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
            return self.failure(str(exc))


class ScalarValidator(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        try:
            Scalar.parse(value)
            return self.success()
        except ScalarParseError as exc:
            return self.failure(str(exc))


class CheckID(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        try:
            check_identifiers("id", value)
            return self.success()
        except BadIdentifier as exc:
            return self.failure(str(exc))


class FloatValidator(Validator):
    def __init__(self) -> None:
        super().__init__("Value is not a float!")

    def validate(self, value: str) -> ValidationResult:
        try:
            float(value)
            return self.success()
        except ValueError:
            return self.failure()


class SpacingValidator(Validator):
    def __init__(self) -> None:
        super().__init__()

    def validate(self, value: str) -> ValidationResult:
        if all(num.isnumeric() for num in value.split()):
            try:
                Spacing.unpack(list(map(lambda x: int(float(x)), value.split())))
                return self.success()
            except ValueError:
                pass
        return self.failure()


class BorderValidator(Validator):
    def __init__(self, type: Literal["border", "outline", "keyline"]) -> None:
        super().__init__()
        self.type = type

    def validate(self, value: str) -> ValidationResult:
        splitted = value.split()
        if len(splitted) == 2:
            # check border condition
            if self.type in ["border", "outline"] and splitted[0] not in [
                "ascii",
                "blank",
                "dashed",
                "double",
                "heavy",
                "hidden",
                "none",
                "hkey",
                "inner",
                "outer",
                "panel",
                "round",
                "solid",
                "tall",
                "thick",
                "vkey",
                "wide",
            ]:
                return self.failure(description=f"{self.type} type is not right.")
            elif self.type == "keyline" and splitted[0] not in [
                "none",
                "thin",
                "heavy",
                "double",
            ]:
                return self.failure("keyline type is not right.")
            # check color
            try:
                Color.parse(splitted[1])
                return self.success()
            except ColorParseError:
                return self.failure("Color could not be parsed. Must be hex code!")
        else:
            return self.failure(
                f"Must have 2 parameters, but {len(splitted)} was provided"
            )
