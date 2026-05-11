from collections.abc import Callable, Collection, Sequence
from contextvars import ContextVar
from http import HTTPMethod, HTTPStatus
from typing import Any

from dishka import AsyncContainer
from dishka.entities.scope import Scope as DishkaScope
from dishka.integrations.base import wrap_injection

from rapis.entities.handler import Handler
from rapis.entities.middleware import Middleware
from rapis.routing import Route
from rapis.types import HttpProtocol, RSGIApp, Scope

_request_async_container: ContextVar[AsyncContainer | None] = ContextVar(
    "rapis_dishka_request_async_container",
    default=None,
)


def get_request_container() -> AsyncContainer:
    container = _request_async_container.get()
    if container is None:
        msg = (
            "Dishka request container is not active. Add "
            "`Middleware(DishkaMiddleware, container)` "
            "to `WebApp.middlewares`."
        )
        raise RuntimeError(msg)
    return container


def _inject_async(func: Callable[..., Any]) -> Callable[..., Any]:
    return wrap_injection(
        func=func,
        is_async=True,
        container_getter=lambda _args, _kwargs: get_request_container(),
    )


class DishkaRoute(Route):
    def __init__(
        self,
        path: str,
        endpoint: Callable | Handler,
        status: HTTPStatus,
        *,
        methods: Collection[HTTPMethod] | None = None,
        middleware: Sequence[Middleware] | None = None,
    ) -> None:
        if isinstance(endpoint, Handler):
            ep = endpoint
        else:
            ep = _inject_async(endpoint)
        super().__init__(
            path, ep, status, methods=methods, middleware=middleware
        )


class DishkaMiddleware:
    """Opens a Dishka REQUEST (or custom) scope for each HTTP request."""

    def __init__(
        self,
        app: RSGIApp,
        container: AsyncContainer,
        *,
        di_scope: DishkaScope = DishkaScope.REQUEST,
        context_factory: Callable[[Scope, HttpProtocol], dict[Any, Any]]
        | None = None,
    ) -> None:
        self.app = app
        self.container = container
        self.di_scope = di_scope
        self.context_factory = context_factory or (lambda _s, _p: {})

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        if scope.proto != "http":
            await self.app(scope, proto)
            return
        context = self.context_factory(scope, proto)
        async with self.container(
            context, scope=self.di_scope
        ) as request_container:
            token = _request_async_container.set(request_container)
            try:
                await self.app(scope, proto)
            finally:
                _request_async_container.reset(token)
