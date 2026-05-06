from http import HTTPStatus

from rapis.types import ExceptionHandler, HttpProtocol, RSGIApp, Scope


class ServerExceptionMiddleware:
    """
        Handles Every Exception to correctly end a request,
        without it request rate goes to low on exceptions

    reraise_exception is recommended to OFF if RPS is very important
    """

    def __init__(
        self,
        app: RSGIApp,
        reraise_exception: bool = True,
        override_handler: ExceptionHandler | None = None,
    ) -> None:
        self.app = app
        self.override_handler = override_handler
        self.reraise_exception = reraise_exception

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        try:
            await self.app(scope, proto)
        except Exception as e:  # noqa: BLE001
            if not self.override_handler:
                await self.default(e, scope, proto)
            else:
                await self.override_handler(e, scope, proto)

    async def default(
        self, exception: Exception, _scope: Scope, proto: HttpProtocol
    ) -> None:

        proto.response_bytes(
            HTTPStatus.INTERNAL_SERVER_ERROR, [], b"Internal Server Error"
        )
        if self.reraise_exception:
            raise exception


class ExceptionMiddleware:
    def __init__(
        self, app: RSGIApp, handlers: dict[type[Exception], ExceptionHandler]
    ) -> None:
        self.app = app
        self.handlers = handlers

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        try:
            await self.app(scope, proto)
            return
        except Exception as e:
            handler = self.handlers.get(type(e))
            if not handler:
                raise
            await handler(e, scope, proto)
