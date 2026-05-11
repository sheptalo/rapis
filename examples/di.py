from dishka import FromDishka, Provider, Scope, make_async_container, provide

from rapis import AppRouter, WebApp
from rapis.entities.middleware import Middleware
from rapis.integration.dishka import DishkaMiddleware, DishkaRoute

router = AppRouter(route_class=DishkaRoute)


class P(Provider):
    @provide(scope=Scope.REQUEST)
    def greeting(self) -> str:
        return "hello"


container = make_async_container(P())


@router.get("/")
async def index(msg: FromDishka[str]) -> str:
    return msg


app = WebApp(
    middlewares=[Middleware(DishkaMiddleware, container)],
)
app.include_router(router)
