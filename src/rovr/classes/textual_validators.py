from os import getcwd, path

from textual.validation import ValidationResult, Validator

from rovr.functions.path import normalise
from rovr.variables.constants import os_type


class IsValidFilePath(Validator):
    def __init__(self, strict: bool = False) -> None:
        super().__init__(failure_description="Path contains illegal characters.")
        self.strict = strict

    def validate(self, value: str) -> ValidationResult:
        from pathvalidate import sanitize_filepath

        value = str(normalise(str(getcwd()) + "/" + value))
        if value == normalise(sanitize_filepath(value)):
            return self.success()
        else:
            return self.failure()


class PathNoLongerExists(Validator):
    def __init__(
        self, accept: list[str] | None = None, accept_equal: bool = False
    ) -> None:
        super().__init__(failure_description="Path already exists.")
        self.accept = accept
        self.accept_equal = accept_equal

    def validate(self, value: str) -> ValidationResult:
        item_path = str(normalise(str(getcwd()) + "/" + value))
        if path.exists(item_path):
            # check for acceptance
            if os_type == "Windows" and self.accept is not None:
                # check
                lower_val = value.lower()
                if any(
                    lower_val == accepted.lower()
                    and (self.accept_equal or value != accepted)
                    for accepted in self.accept
                ):
                    return self.success()
                else:
                    return self.failure()
            else:
                return self.failure(
                    f"A {'folder' if path.isdir(item_path) else 'file'} with that name already exists."
                )
        else:
            return self.success()


class AllowsExistingFiles(Validator):
    def __init__(self) -> None:
        super().__init__(failure_description="Path does not exist.")

    def validate(self, value: str) -> ValidationResult:
        item_path = str(normalise(str(getcwd()) + "/" + value))
        if path.exists(item_path):
            if path.isfile(item_path):
                return self.success()
            else:
                return self.failure("Path is not a file.")
        else:
            return self.success()
