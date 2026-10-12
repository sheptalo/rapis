import logging
from collections.abc import Callable, Sequence
from typing import Any

from rapis.types import (
    HandlerSpec,
    Middleware,
    Parser,
    Serializer,
)

logger = logging.getLogger("rapis")


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
