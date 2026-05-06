from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

from granian._granian import RSGIHTTPProtocol

type RSGIApp = Callable[[Scope, HttpProtocol], Awaitable[None]]
type ExceptionHandler[T: Exception] = Callable[
    [T, Scope, HttpProtocol], Awaitable[None]
]

type Query[T] = T


class HttpProtocol(RSGIHTTPProtocol): ...  # for now


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
