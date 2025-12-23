from os import getcwd, path

from pathvalidate import sanitize_filepath
from textual.validation import ValidationResult, Validator

from rovr.functions.path import normalise
from rovr.variables.constants import os_type


class IsValidFilePath(Validator):
    def __init__(self, strict: bool = False) -> None:
        super().__init__(failure_description="Path contains illegal characers.")
        self.strict = strict

    def validate(self, value: str) -> ValidationResult:
        value = str(normalise(str(getcwd()) + "/" + value))
        if value == normalise(sanitize_filepath(value)):
            return self.success()
        else:
            return self.failure()


class PathDoesntExist(Validator):
    def __init__(self, strict: bool = True, accept: list[str] | None = None) -> None:
        super().__init__(failure_description="Path already exists.")
        self.strict = strict
        self.accept = accept

    def validate(self, value: str) -> ValidationResult:
        item_path = str(normalise(str(getcwd()) + "/" + value))
        if path.exists(item_path):
            # check for acceptance
            if os_type == "Windows" and self.accept is not None:
                # check
                lower_val = value.lower()
                if any(
                    lower_val == accepted.lower() and value != accepted
                    for accepted in self.accept
                ):
                    return self.success()
                else:
                    return self.failure()
            else:
                return self.failure()
        else:
            return self.success()


class EndsWithAnArchiveExtension(Validator):
    def __init__(self) -> None:
        super().__init__(
            failure_description="Extension is not a valid archive type."
        )
        self.strict = True
        self.allowed_extensions: tuple[str]
        allowed: list[str] = []
        from rovr.classes.archive import ARCHIVE_EXTENSIONS
        for exts in ARCHIVE_EXTENSIONS:
            for ext in exts:
                allowed.append(str(ext))
        self.allowed_extensions = tuple(allowed)

    def validate(self, value: str) -> ValidationResult:
        if value.endswith(self.allowed_extensions):
            return self.success()
        else:
            return self.failure()


class EndsWithRar(Validator):
    def __init__(self) -> None:
        super().__init__(failure_description="RAR files cannot be created.")
        self.strict = True

    def validate(self, value: str) -> ValidationResult:
        if value.endswith(".rar"):
            return self.failure()
        else:
            return self.success()
