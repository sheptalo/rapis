import functools
import logging
from asyncio import AbstractEventLoop
from collections.abc import Awaitable, Callable
from typing import Any

import msgspec

from rapis._build import build_dispatch
from rapis.exceptions import HTTPError
from rapis.responses import decode_error, http_error, validation_error
from rapis.router import Router
from rapis.types import (
    ExceptionHandler,
    Handler,
    HttpProtocol,
    Request,
    Response,
    Scope,
)

logger = logging.getLogger("rapis")

type ErrorMapper = Callable[[Exception, Request], Response | None]
type Entry = Callable[[Scope, HttpProtocol], Awaitable[None]]


class App:
    def __init__(
        self,
        router: Router,
        exception_handlers: dict[type, ExceptionHandler[Any]] | None = None,
    ) -> None:
        self.router = router
        self.exception_handlers: dict[type, ExceptionHandler[Any]] = {
            HTTPError: http_error,
            msgspec.ValidationError: validation_error,
            msgspec.DecodeError: decode_error,
            **(exception_handlers or {}),
        }
        self._entry: Entry = self._build_and_handle

    def __rsgi_init__(self, loop: AbstractEventLoop) -> None:
        self.build()

    def __rsgi__(self, scope: Scope, proto: HttpProtocol) -> Awaitable[None]:
        return self._entry(scope, proto)

    def build(self) -> None:
        resolve = build_dispatch(self.router)
        map_error = _error_mapper(self.exception_handlers)
        if self.router.outer_middlewares:
            call = _serve(resolve, map_error)
            for mw in reversed(self.router.outer_middlewares):
                call = functools.partial(mw, call)
            self._entry = _entry_chain(call, map_error)
        else:
            self._entry = _entry_direct(resolve, map_error)

    async def _build_and_handle(self, scope: Any, proto: Any) -> None:
        self.build()
        await self._entry(scope, proto)


def _error_mapper(
    handlers: dict[type, ExceptionHandler[Any]],
) -> ErrorMapper:
    @functools.cache
    def lookup(mro: tuple[type, ...]) -> ExceptionHandler[Any] | None:
        return next((handlers[k] for k in mro if k in handlers), None)

    def map_error(exc: Exception, req: Request) -> Response | None:
        handler = lookup(type(exc).__mro__)
        return None if handler is None else handler(exc, req)

    return map_error


def _serve(
    resolve: Callable[[Request], Handler], map_error: ErrorMapper
) -> Handler:
    async def serve(req: Request) -> Response:
        try:
            return await resolve(req)(req)
        except Exception as exc:
            response = map_error(exc, req)
            if response is None:
                raise
            return response

    return serve


def _entry_direct(
    resolve: Callable[[Request], Handler], map_error: ErrorMapper
) -> Entry:
    async def entry(scope: Scope, proto: HttpProtocol) -> None:
        req = Request(scope, proto)
        try:
            response: Response | None
            try:
                response = await resolve(req)(req)
            except Exception as exc:
                response = map_error(exc, req)
                if response is None:
                    raise
        except Exception:
            logger.exception("unhandled error")
            response = Response(500, [], b"Internal Server Error")
        proto.response_bytes(response.status, response.headers, response.body)

    return entry


def _entry_chain(call: Handler, map_error: ErrorMapper) -> Entry:
    async def entry(scope: Scope, proto: HttpProtocol) -> None:
        req = Request(scope, proto)
        try:
            response: Response | None
            try:
                response = await call(req)
            except Exception as exc:
                response = map_error(exc, req)
                if response is None:
                    raise
        except Exception:
            logger.exception("unhandled error")
            response = Response(500, [], b"Internal Server Error")
        proto.response_bytes(response.status, response.headers, response.body)

    return entry
