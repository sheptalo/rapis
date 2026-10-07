class BuildError(Exception): ...


class HTTPError(Exception):
    def __init__(self, status: int, detail: str = "") -> None:
        super().__init__(status, detail)
        self.status = status
        self.detail = detail
