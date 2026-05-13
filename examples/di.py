from dishka import FromDishka, Provider, Scope, make_async_container, provide

from rapis import AppRouter, WebApp
from rapis.entities.middleware import Middleware
from rapis.integration.dishka import (
    DishkaMiddleware,
    DishkaRoute,
    RapisProvider,
)
from rapis.types import Scope as WebScope

router = AppRouter(route_class=DishkaRoute)


class P(Provider):
    @provide(scope=Scope.REQUEST)
    def scope_path(self, scope: WebScope) -> str:
        return scope.path


container = make_async_container(P(), RapisProvider())


@router.get("/{path}")
async def full_path(
    path: str, msg: FromDishka[str], scope: FromDishka[WebScope]
) -> dict:
    return {
        "path_parameter": path,
        "scope_path": msg,
        "scope_itself": scope.path,
    }


app = WebApp(
    middlewares=[Middleware(DishkaMiddleware, container)],
)
app.include_router(router)
