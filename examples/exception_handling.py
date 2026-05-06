from rapis import AppRouter, WebApp
from rapis.types import HttpProtocol, Scope

router = AppRouter()


class NotHandledError(Exception): ...


async def value_error_handler(
    exc: ValueError, _scope: Scope, proto: HttpProtocol
) -> None:
    proto.response_str(400, [], str(exc))


async def internal_server_error_handler(
    exc: Exception, _scope: Scope, proto: HttpProtocol
) -> None:
    proto.response_str(500, [], str(exc))


@router.get("/")
async def root() -> dict:
    raise ValueError


@router.get("/500")
async def internal_server_error() -> dict:
    raise NotHandledError


app = WebApp()
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, internal_server_error_handler)
app.include_router(router)
