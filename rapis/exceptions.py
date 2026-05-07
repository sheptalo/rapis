class RapisError(Exception): ...


class ValidationError(RapisError):
    errors: dict[str, str]

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
