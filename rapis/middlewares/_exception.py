from http import HTTPStatus

import msgspec
from msgspec import DecodeError

from rapis.exceptions import ValidationError
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
        self.encoder = msgspec.json.Encoder()

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        try:
            await self.app(scope, proto)
            return
        except Exception as e:
            handler = self.handlers.get(type(e))
            if not handler:
                if isinstance(e, ValidationError):
                    await self.default_validation_error(e, scope, proto)
                elif isinstance(e, DecodeError):
                    await self.default_decode_error(e, scope, proto)
                else:
                    raise
            else:
                await handler(e, scope, proto)

    async def default_validation_error(
        self, exc: ValidationError, _scope: Scope, proto: HttpProtocol
    ) -> None:
        proto.response_bytes(
            400,
            [("Content-Type", "application/json")],
            self.encoder.encode(exc.errors),
        )

    async def default_decode_error(
        self, _: DecodeError, _scope: Scope, proto: HttpProtocol
    ) -> None:
        proto.response_bytes(
            400,
            [("Content-Type", "application/json")],
            b'{"detail": "JSON Decode Error"}',
        )
