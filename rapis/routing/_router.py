from collections.abc import Callable, Sequence
from http import HTTPMethod, HTTPStatus
from typing import Any, Unpack

from rapis.entities.middleware import Middleware
from rapis.entities.route import Route
from rapis.routing import APIRoute
from rapis.types import (
    HttpProtocol,
    RouteOptions,
    RSGIApp,
    Scope,
)


class AppRouter:
    def __init__(
        self,
        prefix: str = "",
        middlewares: Sequence[Middleware] | None = None,
        *,
        default: RSGIApp | None = None,
        route_class: type[Route] = APIRoute,
        tags: Sequence[str] | None = None,
    ) -> None:
        if not middlewares:
            middlewares = []
        self.prefix = prefix
        self.dynamic_routes: list[Route] = []
        self.static_routes: dict[str, Route] = {}
        self.exception_handlers = []
        self.middlewares = middlewares
        self.route_class = route_class
        self.default = default or self.not_found
        self.tags = tags or []

    def route(
        self,
        url: str,
        *,
        methods: list[HTTPMethod],
        status: HTTPStatus = HTTPStatus.OK,
        description: str = "",
        summary: str = "",
    ) -> Callable:
        def deco(func: Callable) -> Callable:
            route = self.route_class(
                path=self.prefix + url,
                endpoint=func,
                status=status,
                methods=methods,
                middleware=self.middlewares,
                tags=self.tags,
                description=description,
                summary=summary,
            )
            if route.static():
                self.static_routes[url] = route
            else:
                self.dynamic_routes.append(route)
            return func

        return deco

    def post(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(url, methods=[HTTPMethod.POST], **opts)

    def head(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.HEAD], **opts)

    def get(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(
            url, methods=[HTTPMethod.GET, HTTPMethod.HEAD], **opts
        )

    def patch(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.PATCH], **opts)

    def put(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.PUT], **opts)

    def delete(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(
            url,
            methods=[HTTPMethod.DELETE],
            **RouteOptions(status=HTTPStatus.NO_CONTENT, **opts),
        )

    def trace(
        self, url: str, **opts: Unpack[RouteOptions]
    ) -> Callable[[Callable], Callable]:
        return self.route(url, methods=[HTTPMethod.TRACE], **opts)

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> Any:
        static_route = self.static_routes.get(scope.path)
        if static_route:
            await static_route(scope, proto)
            return
        for route in self.dynamic_routes:
            if route.matches(scope):
                await route(scope, proto)
                break
        else:
            await self.default(scope, proto)

    async def not_found(self, scope: Scope, proto: HttpProtocol) -> Any:
        if scope.scheme == "http":
            proto.response_bytes(
                HTTPStatus.NOT_FOUND,
                [("Content-type", "application/json")],
                b'{"detail":"Not Found"}',
            )
