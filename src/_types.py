from collections.abc import Awaitable, Callable

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

type RSGIApp = Callable[[Scope, RSGIHTTPProtocol], Awaitable[None]]


class Query[T]:
    def __init__(self, default: T | None = None) -> None:
        self.default = default
