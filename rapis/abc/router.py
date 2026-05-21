from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from rapis.abc.middleware import Middleware
from rapis.abc.route import Route
from rapis.types import HttpProtocol, RSGIApp, Scope


class Router(Protocol):
    prefix: str
    middlewares: Sequence[Middleware]
    route_class: type[Route]
    tags: Sequence[str]

    def __init__(
        self,
        prefix: str = "",
        middlewares: Sequence[Middleware] | None = None,
        *,
        route_class: type[Route] = ...,
        default: RSGIApp | None = None,
        tags: Sequence[str] | None = None,
    ) -> None: ...

    def mount(self, routes: Iterable[Route]) -> None: ...
    async def __call__(self, scope: Scope, proto: HttpProtocol) -> Any: ...
    @property
    def routes(self) -> Iterable[Route]: ...
