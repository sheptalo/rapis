from collections.abc import Callable, Sequence
from http import HTTPMethod, HTTPStatus
from typing import Any

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

from ._handler import Handler
from ._middleware import Middleware
from ._route import Route
from ._types import RSGIApp


class AppRouter:
    def __init__(  # TODO(): exception handle
        self,
        prefix: str = "",
        middlewares: Sequence[Middleware] | None = None,
        *,
        default: RSGIApp | None = None,
        route_class: type[Route] = Route,
    ) -> None:
        if not middlewares:
            middlewares = []
        self.prefix = prefix
        self.routes: list[Route] = []
        self.middlewares = middlewares
        self.route_class = route_class
        self.default = default or self.not_found

    def route(
        self,
        url: str,
        methods: list[HTTPMethod],
        *,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> Callable:
        def deco(func: Callable) -> Callable:
            self.routes.append(
                self.route_class(
                    path=self.prefix + url,
                    endpoint=Handler(func, status=status),
                    methods=methods,
                    middleware=self.middlewares,
                )
            )
            return func

        return deco

    def head(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(
            url, methods=[HTTPMethod.GET, HTTPMethod.HEAD], status=status
        )

    def get(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(
            url, methods=[HTTPMethod.GET, HTTPMethod.OPTIONS], status=status
        )

    def post(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.POST], status=status)

    def patch(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.PATCH], status=status)

    def put(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.PUT], status=status)

    def delete(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.DELETE], status=status)

    def trace(
        self, url: str, *, status: HTTPStatus = HTTPStatus.OK
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.TRACE], status=status)

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> Any:
        for route in self.routes:
            if route.matches(scope):
                await route(scope, proto)
                break
        else:
            await self.default(scope, proto)

    async def not_found(self, scope: Scope, proto: RSGIHTTPProtocol) -> Any:
        if scope.scheme == "http":
            proto.response_str(
                HTTPStatus.NOT_FOUND,
                [("Content-type", "application/json")],
                '{"detail":"Not Found"',
            )
