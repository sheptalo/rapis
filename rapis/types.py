from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal, Protocol

type RSGIApp = Callable[[Scope, HttpProtocol], Awaitable[None]]
type ExceptionHandler[T: Exception] = Callable[
    [T, Scope, HttpProtocol], Awaitable[None]
]

type Query[T] = T


class HttpProtocol(Protocol):  # source: granian .pyi file
    async def __call__(self) -> bytes: ...
    def __aiter__(self) -> Any: ...
    async def client_disconnect(self) -> None: ...
    def response_empty(
        self, status: int, headers: list[tuple[str, str]]
    ) -> None: ...
    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None: ...
    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None: ...
    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None: ...
    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None: ...
    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> Any: ...


class Scope:  # source: https://github.com/emmett-framework/granian/blob/master/docs/spec/RSGI.md
    proto: Literal["http", "ws"]
    rsgi_version: str
    http_version: str
    server: str
    client: str
    scheme: str
    method: str
    path: str
    query_string: str
    headers: Mapping[str, str]
    authority: str | None
