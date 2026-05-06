from msgspec import Struct

from rapis import AppRouter, Query, WebApp

router = AppRouter()


@router.get("/")
async def url_with_default_query(name: Query[str] = "default") -> dict:
    return {"Hello": name}


@router.get("/")
async def url_without_default_query(name: Query[str]) -> dict:
    return {"Hello": f"required {name}"}


class User(Struct):
    name: str


@router.get("/")
async def url_with_default_query_struct(
    user: Query[User] = User(""),
) -> User:  # it is recommend to not change your default structs
    return user


@router.get("/")
async def url_without_default_query_struct(user: Query[User]) -> User:
    return user


app = WebApp()

app.include_router(router)
