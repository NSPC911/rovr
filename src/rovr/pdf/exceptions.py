class PDFRuntimeError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.__traceback__ = None


class NotAPDFError(NameError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.__traceback__ = None


class PDFHasAPasswordError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.__traceback__ = None
