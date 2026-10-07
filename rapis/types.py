import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

try:
    from rapis._speedups import parse_query
except ImportError:
    from rapis._query import parse_query


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


class Scope(
    Protocol
):  # source: https://github.com/emmett-framework/granian/blob/master/docs/spec/RSGI.md
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


class Response:
    __slots__ = ("status", "headers", "body")

    def __init__(
        self,
        status: int = 200,
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self.headers = headers if headers is not None else []
        self.body = body


class Request:
    __slots__ = ("scope", "proto", "path_params", "state", "body", "_query")

    def __init__(self, scope: Scope, proto: HttpProtocol) -> None:
        self.scope = scope
        self.proto = proto
        self.path_params: dict[str, str] = {}
        self.state: dict[str, Any] = {}
        self.body = b""
        self._query: dict[str, str] | None = None

    @property
    def query(self) -> dict[str, str]:
        if self._query is None:
            qs = self.scope.query_string
            self._query = parse_query(qs) if qs else {}
        return self._query


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    type: Any
    default: Any

    @property
    def required(self) -> bool:
        return self.default is inspect.Parameter.empty


type Handler = Callable[[Request], Awaitable[Response]]
type ExceptionHandler[T] = Callable[[T, Request], Response]


class Middleware(Protocol):
    async def __call__(
        self, handler: Handler, request: Request
    ) -> Response: ...


class Parser(Protocol):
    needs_body: bool
    fields: Sequence[str] | None

    def build(
        self, params: list[Param]
    ) -> Callable[[Request], dict[str, Any]]: ...


class Serializer(Protocol):
    def build(self, tp: Any, status: int) -> Callable[[Any], Response]: ...


@dataclass(slots=True)
class HandlerSpec:
    func: Callable[..., Awaitable[Any]]
    path: str
    methods: tuple[str, ...]
    status: int
