import sys
from os import path

from rich.highlighter import Highlighter
from rich.text import Text
from textual.validation import ValidationResult, Validator

from rovr.functions.cwd import getcwd
from rovr.functions.path import control, normalise


class IsValidFilePath(Validator):
    def __init__(self, strict: bool = False) -> None:
        super().__init__(failure_description="Path contains illegal characters.")
        self.strict = strict

    def validate(self, value: str) -> ValidationResult:
        from pathvalidate import sanitize_filepath

        # Handle absolute paths correctly
        if path.isabs(value):
            normalized_value = normalise(value)
        else:
            normalized_value = normalise(str(getcwd()) + "/" + value)

        if normalized_value == normalise(sanitize_filepath(normalized_value)):
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
        # Handle absolute paths correctly
        if path.isabs(value):
            item_path = normalise(value)
        else:
            item_path = normalise(str(getcwd()) + "/" + value)

        if path.exists(item_path):
            # check for acceptance
            if sys.platform == "win32" and self.accept is not None:
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


# look, i dont know where to put this, but since Validator is used by Input
# and Highlighter can be used by Input, it makes sense to put this here
class ControlHighlighter(Highlighter):
    def __call__(self, text: str | Text) -> Text:
        """Highlight a str or Text instance.

        Args:
            text (Union[str, ~Text]): Text to highlight.

        Raises:
            TypeError: If not called with text or str.

        Returns:
            Text: A test instance with highlighting applied.
        """
        if isinstance(text, str):
            highlight_text = Text(control(text), end="")
        elif isinstance(text, Text):
            # not markup btw, Text doesn't instantly use markup
            highlight_text = Text(control(text.plain), end="")
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")
        return highlight_text

    def highlight(self, text: Text) -> None: ...  # because we are doing it in __call__
