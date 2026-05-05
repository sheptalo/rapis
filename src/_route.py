from collections.abc import Callable, Collection, Sequence
from http import HTTPMethod, HTTPStatus
from typing import Any

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

from ._middleware import Middleware


class Route:
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Collection[HTTPMethod] | None = None,
        middleware: Sequence[Middleware] | None = None,
    ) -> None:
        self.path = path
        self.endpoint = endpoint
        self.app = endpoint

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)

        if methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> None:
        await self.handle(scope, proto)

    def matches(self, scope: Scope) -> bool:
        return scope.path == scope.path

    async def handle(
        self,
        scope: Scope,
        proto: RSGIHTTPProtocol,
    ) -> None:
        if self.methods and scope.method not in self.methods:
            headers = [("Allow", ", ".join(sorted(self.methods)))]
            proto.response_str(
                HTTPStatus.METHOD_NOT_ALLOWED, headers, "Method Not Allowed"
            )
            return

        await self.app(scope, proto)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Route)
            and self.path == other.path
            and self.endpoint == other.endpoint
            and self.methods == other.methods
        )

    def __hash__(self) -> int:
        return hash(self.path)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(path={self.path!r}, "
            f"methods={sorted(self.methods or [])!r})"
        )
