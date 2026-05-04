from collections.abc import Sequence
from functools import reduce

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

from ._middleware import Middleware
from ._router import AppRouter
from ._types import RSGIApp


class WebApp:
    def __init__(
        self,
        *,
        root_path: str = "",
        middlewares: Sequence[Middleware] | None = None,
    ) -> None:
        if not middlewares:
            middlewares = []
        self.router = AppRouter(prefix=root_path)
        self.root_path = root_path
        self.middleware_stack: RSGIApp = reduce(
            lambda app, mw: mw.cls(app, *mw.args, **mw.kwargs),
            reversed(middlewares),
            self.router,
        )

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> None:
        await self.middleware_stack(scope, proto)

    def include_router(self, router: AppRouter) -> None:
        for route in router.routes:
            route.path = self.router.prefix + route.path
            self.router.routes.append(route)
