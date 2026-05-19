from abc import ABC, abstractmethod
from collections.abc import Callable, Collection, Sequence
from http import HTTPMethod, HTTPStatus
from typing import Any

from rapis.entities.handler import Handler
from rapis.entities.middleware import Middleware
from rapis.types import HttpProtocol, Scope


class Route(ABC):
    path: str
    handler: Handler
    status: HTTPStatus
    methods: Collection[HTTPMethod]
    description: str | None = ""
    summary: str | None = ""
    tags: Sequence[str] | None = None

    @abstractmethod
    def __init__(
        self,
        path: str,
        endpoint: Callable | Handler,
        status: HTTPStatus,
        *,
        methods: Collection[HTTPMethod] | None = None,
        middleware: Sequence[Middleware] | None = None,
        description: str | None = "",
        summary: str | None = "",
        tags: Sequence[str] | None = None,
    ) -> None: ...

    @abstractmethod
    async def __call__(self, scope: Scope, proto: HttpProtocol) -> Any:
        pass

    @abstractmethod
    def matches(self, scope: Scope) -> bool: ...

    @abstractmethod
    def static(self) -> bool: ...
