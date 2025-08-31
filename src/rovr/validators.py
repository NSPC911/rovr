from os import getcwd, path

from pathvalidate import sanitize_filepath
from textual.validation import ValidationResult, Validator

from rovr.utils import normalise


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
    def __init__(self, strict: bool = True) -> None:
        super().__init__(failure_description="Path already exists.")
        self.strict = strict

    def validate(self, value: str) -> ValidationResult:
        value = str(normalise(str(getcwd()) + "/" + value))
        if path.exists(value):
            return self.failure()
        else:
            return self.success()


class EndsWithAnArchiveExtension(Validator):
    def __init__(self) -> None:
        super().__init__(
            failure_description="Path does not end with a valid extension."
        )
        self.strict = True

    def validate(self, value: str) -> ValidationResult:
        if value.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".zip")):
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
