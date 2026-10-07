import functools
import logging
from asyncio import AbstractEventLoop
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import msgspec

from rapis._build import build_dispatch, json_response
from rapis.exceptions import HTTPError
from rapis.types import (
    ExceptionHandler,
    Handler,
    HandlerSpec,
    HttpProtocol,
    Middleware,
    Parser,
    Request,
    Response,
    Scope,
    Serializer,
)

logger = logging.getLogger("rapis")


class CORSMiddleware:
    def __init__(
        self,
        allow_origins: Sequence[str] = ("*",),
        allow_methods: Sequence[str] = (
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ),
        max_age: int = 600,
    ) -> None:
        self.origins = frozenset(allow_origins)
        self.any_origin = "*" in self.origins
        self.preflight = [
            ("access-control-allow-methods", ", ".join(allow_methods)),
            ("access-control-max-age", str(max_age)),
        ]

    async def __call__(self, handler: Handler, request: Request) -> Response:
        headers = request.scope.headers
        origin = headers.get("origin")
        if origin is None or not (self.any_origin or origin in self.origins):
            return await handler(request)
        cors = [
            (
                "access-control-allow-origin",
                "*" if self.any_origin else origin,
            ),
            ("vary", "origin"),
        ]
        if request.scope.method == "OPTIONS" and headers.get(
            "access-control-request-method"
        ):
            requested = headers.get("access-control-request-headers")
            extra = (
                [("access-control-allow-headers", requested)]
                if requested
                else []
            )
            return Response(204, cors + self.preflight + extra)
        response = await handler(request)
        response.headers = response.headers + cors
        return response


class Router:
    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix
        self.children: list[Router] = []
        self.handlers: list[HandlerSpec] = []
        self.outer_middlewares: list[Middleware] = []
        self.middlewares: list[Middleware] = []
        self.parser: Parser | None = None
        self.serializer: Serializer | None = None

    def include_router(self, router: "Router") -> None:
        self.children.append(router)

    def route(
        self,
        path: str,
        methods: Sequence[str] = ("*",),
        status: int = 200,
    ) -> Callable[..., Any]:
        upper = tuple(m.upper() for m in methods)

        def deco(func: Callable[..., Any]) -> Callable[..., Any]:
            self.handlers.append(HandlerSpec(func, path, upper, status))
            return func

        return deco

    def get(self, path: str, status: int = 200) -> Callable[..., Any]:
        return self.route(path, methods=("GET",), status=status)

    def post(self, path: str, status: int = 200) -> Callable[..., Any]:
        return self.route(path, methods=("POST",), status=status)


def _http_error(exc: HTTPError, _req: Request) -> Response:
    return json_response(exc.status, {"detail": exc.detail})


def _validation_error(exc: msgspec.ValidationError, _req: Request) -> Response:
    return json_response(400, {"detail": str(exc)})


def _decode_error(_exc: msgspec.DecodeError, _req: Request) -> Response:
    return json_response(400, {"detail": "JSON Decode Error"})


class App:
    def __init__(
        self,
        router: Router,
        exception_handlers: dict[type, ExceptionHandler[Any]] | None = None,
    ) -> None:
        self.router = router
        self.exception_handlers: dict[type, ExceptionHandler[Any]] = {
            HTTPError: _http_error,
            msgspec.ValidationError: _validation_error,
            msgspec.DecodeError: _decode_error,
            **(exception_handlers or {}),
        }
        self._entry = self._build_and_handle

    def __rsgi_init__(self, loop: AbstractEventLoop) -> None:
        self.build()

    def __rsgi__(self, scope: Scope, proto: HttpProtocol) -> Awaitable[None]:
        return self._entry(scope, proto)

    def build(self) -> None:
        dispatch = build_dispatch(self.router)
        handlers = self.exception_handlers

        @functools.cache
        def lookup(mro: tuple[type, ...]) -> ExceptionHandler[Any] | None:
            return next((handlers[k] for k in mro if k in handlers), None)

        async def guarded(req: Request) -> Response:
            try:
                return await dispatch(req)
            except Exception as exc:
                handler = lookup(type(exc).__mro__)
                if handler is None:
                    raise
                return handler(exc, req)

        call = guarded
        for mw in reversed(self.router.outer_middlewares):
            call = functools.partial(mw, call)

        async def entry(scope: Scope, proto: HttpProtocol) -> None:
            try:
                response = await call(Request(scope, proto))
            except Exception:
                logger.exception("unhandled error")
                response = Response(500, [], b"Internal Server Error")
            proto.response_bytes(
                response.status, response.headers, response.body
            )

        self._entry = entry

    async def _build_and_handle(self, scope: Any, proto: Any) -> None:
        self.build()
        await self._entry(scope, proto)
