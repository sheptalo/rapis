import inspect
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import msgspec

try:
    from rapis._speedups import parse_query
except ImportError:
    from rapis._query import parse_query

SERIALIZER_LITERAL = "__rapis_serializer__"
PARSER_LITERAL = "__rapis_parsers__"


type Header = tuple[str, str]
type Headers = list[Header]
type Step = Callable[[Request, dict[str, Any]], None]
type Walked = tuple[
    HandlerSpec, str, tuple[Middleware, ...], Parser | None, Serializer | None
]
type Dynamic = tuple[dict[str, Any], list[tuple[str, int]]]
type Matcher = tuple[
    Callable[[str], re.Match[str] | None], dict[int | None, Dynamic]
]
PARAM = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class HttpProtocol(Protocol):
    async def __call__(self) -> bytes: ...
    def __aiter__(self) -> Any: ...
    async def client_disconnect(self) -> None: ...
    def response_empty(self, status: int, headers: Headers) -> None: ...
    def response_str(
        self, status: int, headers: Headers, body: str
    ) -> None: ...
    def response_bytes(
        self, status: int, headers: Headers, body: bytes
    ) -> None: ...
    def response_file(
        self, status: int, headers: Headers, file: str
    ) -> None: ...
    def response_file_range(
        self, status: int, headers: Headers, file: str, start: int, end: int
    ) -> None: ...
    def response_stream(self, status: int, headers: Headers) -> Any: ...


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


class Response(msgspec.Struct):
    status: int = 200
    headers: Headers = msgspec.field(default_factory=list)
    body: bytes = b""


class Request(msgspec.Struct):
    scope: Scope
    proto: HttpProtocol
    path_params: dict[str, str] = msgspec.field(default_factory=dict)
    state: dict[str, Any] = msgspec.field(default_factory=dict)
    body: bytes = b""
    _query: dict[str, str] | None = None

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


type ParserCallable = Callable[[Request], dict[str, Any]]


class Parser:
    fields: Sequence[str] | None
    needs_body: bool

    def __call__[F: Callable[..., Any]](self, func: F) -> F:
        func.__dict__.setdefault(PARSER_LITERAL, []).append(self)
        return func

    def build(self, params: list[Param]) -> ParserCallable:
        raise NotImplementedError


type SerializerCallable = Callable[[Any], Response]


class Serializer:
    def __call__[F: Callable[..., Any]](self, func: F) -> F:
        setattr(func, SERIALIZER_LITERAL, self)
        return func

    def build(self, tp: Any, status: int) -> SerializerCallable:
        raise NotImplementedError


@dataclass(slots=True)
class HandlerSpec:
    func: Callable[..., Awaitable[Any]]
    path: str
    methods: tuple[str, ...]
    status: int
