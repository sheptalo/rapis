from functools import reduce

from rapis.entities.middleware import Middleware
from rapis.middlewares._exception import (
    ExceptionMiddleware,
    ServerExceptionMiddleware,
)
from rapis.routing import AppRouter
from rapis.types import ExceptionHandler, HttpProtocol, RSGIApp, Scope


class WebApp:
    def __init__(
        self,
        *,
        root_path: str = "",
        middlewares: list[Middleware] | None = None,
        router_class: type[AppRouter] = AppRouter,
        reraise_exception: bool = True,
    ) -> None:
        self.reraise_exception = reraise_exception
        if not middlewares:
            middlewares = []
        self.middlewares: list = middlewares
        self.exception_handlers: list[
            tuple[type[Exception], ExceptionHandler]
        ] = []
        self.router = router_class(prefix=root_path)
        self.root_path = root_path
        self.middleware_stack: RSGIApp | None = None

    def build_middleware_stack(self) -> RSGIApp:
        exception_handlers = dict(self.exception_handlers)
        return reduce(
            lambda app, mw: mw.cls(app, *mw.args, **mw.kwargs),
            reversed(
                [
                    Middleware(
                        ServerExceptionMiddleware,
                        reraise_exception=self.reraise_exception,
                        override_handler=exception_handlers.pop(
                            Exception, None
                        ),
                    ),
                    *self.middlewares,
                    Middleware(
                        ExceptionMiddleware,
                        handlers=exception_handlers,
                    ),
                ],
            ),
            self.router,
        )

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        if not self.middleware_stack:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, proto)

    def include_router(self, router: AppRouter) -> None:
        for route in router.routes:
            route.path = self.router.prefix + route.path
            self.router.routes.append(route)

    def add_exception_handler[T: Exception](
        self, exception: type[T], handler: ExceptionHandler[T]
    ) -> None:
        """
        if you want to override default 500,
        register exception handler with Exception type
        """
        self.exception_handlers.append((exception, handler))
