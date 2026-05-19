from http import HTTPStatus

from msgspec import Struct

from rapis import AppRouter, Query, WebApp

primitive_router = AppRouter(tags=["primitives"])


@primitive_router.post(
    "/default-str",
    description="lolasd",
    status=HTTPStatus.ACCEPTED,
    summary="sadsad",
)
async def url_with_default_query(name: Query[str] = "default") -> dict:
    return {"Hello": name}


@primitive_router.post("/required-str")
async def url_without_default_query(name: Query[str]) -> dict:
    return {"Hello": f"required {name}"}


@primitive_router.delete("/delete")
async def delete() -> None:
    pass


struct_router = AppRouter(tags=["struct"])


class User(Struct):
    name: str


class NestedUser(Struct):
    count: int
    users: list[User]


@struct_router.post("/struct-default")
async def url_with_default_query_struct(
    user: User = User(""),
) -> User:  # it is recommend to not change your default structs
    return user


@struct_router.post("/struct-required")
async def url_without_default_query_struct(user: User) -> User:
    return user


@struct_router.post("/list")
async def lis() -> NestedUser:
    return NestedUser(count=1, users=[User(name="1")])


app = WebApp()

app.include_router(struct_router)
app.include_router(primitive_router)
