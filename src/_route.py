from collections.abc import Callable, Collection, Sequence
from http import HTTPMethod, HTTPStatus
from typing import Any

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

from ._handler import (
    Handler,
    path_params_context_token,
    reset_path_params_context,
)
from ._middleware import Middleware
from ._path_pattern import compile_route_path, match_route_path


class Route:
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Collection[HTTPMethod] | None = None,
        middleware: Sequence[Middleware] | None = None,
    ) -> None:
        self._path = path
        self._compiled, self._path_field_names = compile_route_path(path)
        self.endpoint = endpoint

        if isinstance(endpoint, Handler):
            endpoint.set_path_fields(self._path_field_names)

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

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._path = value
        self._compiled, self._path_field_names = compile_route_path(value)
        if isinstance(self.endpoint, Handler):
            self.endpoint.set_path_fields(self._path_field_names)

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> None:
        matched = match_route_path(self._compiled, scope.path)
        if matched is None:
            proto.response_str(HTTPStatus.NOT_FOUND, [], "Not found")
            return
        await self.handle(scope, proto, matched)

    def matches(self, scope: Scope) -> bool:
        return match_route_path(self._compiled, scope.path) is not None

    async def handle(
        self,
        scope: Scope,
        proto: RSGIHTTPProtocol,
        matched: dict[str, str],
    ) -> None:
        if self.methods and scope.method not in self.methods:
            headers = [("Allow", ", ".join(sorted(self.methods)))]
            proto.response_str(
                HTTPStatus.METHOD_NOT_ALLOWED, headers, "Method Not Allowed"
            )
            return

        token = path_params_context_token(matched)
        try:
            await self.app(scope, proto)
        finally:
            reset_path_params_context(token)

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
