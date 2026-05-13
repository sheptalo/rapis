import re
from collections.abc import Collection, Mapping, Sequence
from fnmatch import fnmatch
from http import HTTPMethod, HTTPStatus
from re import Pattern
from typing import Any

from rapis.types import HttpProtocol, RSGIApp, Scope


def _header_get(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.lower()
    if hasattr(headers, "get"):
        v = headers.get(lowered)
        if v is not None:
            return str(v)
    for key, value in headers.items():
        if key.lower() == lowered:
            return str(value)
    return None


def _merge_cors_headers(
    cors_headers: list[tuple[str, str]], headers: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    return [*cors_headers, *headers]


class _HttpProtocolCORS:
    __slots__ = ("_proto", "_cors")

    def __init__(
        self, proto: HttpProtocol, cors_headers: list[tuple[str, str]]
    ) -> None:
        self._proto = proto
        self._cors = cors_headers

    def __getattr__(self, name: str) -> Any:
        return getattr(self._proto, name)

    async def __call__(self) -> bytes:
        return await self._proto()

    def __aiter__(self) -> Any:
        return self._proto.__aiter__()

    async def client_disconnect(self) -> None:
        return await self._proto.client_disconnect()

    def response_empty(
        self, status: int, headers: list[tuple[str, str]]
    ) -> None:
        return self._proto.response_empty(
            status, _merge_cors_headers(self._cors, headers)
        )

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        return self._proto.response_str(
            status, _merge_cors_headers(self._cors, headers), body
        )

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        return self._proto.response_bytes(
            status, _merge_cors_headers(self._cors, headers), body
        )

    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None:
        return self._proto.response_file(
            status, _merge_cors_headers(self._cors, headers), file
        )

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        return self._proto.response_file_range(
            status, _merge_cors_headers(self._cors, headers), file, start, end
        )

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> Any:
        return self._proto.response_stream(
            status, _merge_cors_headers(self._cors, headers)
        )


class CORSMiddleware:
    def __init__(
        self,
        app: RSGIApp,
        *,
        allow_origins: Sequence[str] = ("*",),
        allow_origin_regex: str | Pattern[str] | None = None,
        allow_methods: Collection[HTTPMethod | str] = (
            HTTPMethod.DELETE,
            HTTPMethod.GET,
            HTTPMethod.HEAD,
            HTTPMethod.OPTIONS,
            HTTPMethod.PATCH,
            HTTPMethod.POST,
            HTTPMethod.PUT,
        ),
        allow_headers: Sequence[str] = ("*",),
        allow_credentials: bool = False,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        self.app = app
        self.allow_origins = tuple(allow_origins)
        self.allow_origin_regex = (
            re.compile(allow_origin_regex)
            if isinstance(allow_origin_regex, str)
            else allow_origin_regex
        )
        self.allow_methods = tuple(
            m.value if isinstance(m, HTTPMethod) else str(m).upper()
            for m in allow_methods
        )
        self.allow_headers = {h.lower() for h in allow_headers}
        self.allow_headers_any = "*" in self.allow_headers
        self.allow_credentials = allow_credentials
        self.expose_headers = tuple(expose_headers)
        self.max_age = max_age

        if self.allow_credentials and "*" in self.allow_origins:
            msg = "allow_credentials requires explicit allow_origins, not '*'"
            raise ValueError(msg)

    def _origin_allowed(self, origin: str | None) -> bool:
        if origin is None:
            return False
        if "*" in self.allow_origins:
            return True
        if origin in self.allow_origins:
            return True
        for pattern in self.allow_origins:
            glob_like = "*" in pattern or "?" in pattern or "[" in pattern
            if glob_like and fnmatch(origin, pattern):
                return True
        if self.allow_origin_regex is not None:
            return self.allow_origin_regex.fullmatch(origin) is not None
        return False

    def _allow_origin_value(self, origin: str | None) -> str | None:
        if not self._origin_allowed(origin):
            return None
        if "*" in self.allow_origins and not self.allow_credentials:
            return "*"
        return origin

    def _preflight_allow_headers(self, requested: str | None) -> str:
        if not requested:
            return ""
        if self.allow_headers_any:
            return requested
        pieces = [h.strip().lower() for h in requested.split(",") if h.strip()]
        allowed = [h for h in pieces if h in self.allow_headers]
        return ", ".join(allowed)

    def _cors_response_headers(
        self, scope: Scope, *, preflight: bool
    ) -> list[tuple[str, str]]:
        origin = _header_get(scope.headers, "origin")
        allow_value = self._allow_origin_value(origin)
        if allow_value is None:
            return []

        headers: list[tuple[str, str]] = [
            ("Access-Control-Allow-Origin", allow_value),
            ("Vary", "Origin"),
        ]
        if self.allow_credentials:
            headers.append(("Access-Control-Allow-Credentials", "true"))

        if preflight:
            headers.append(
                (
                    "Access-Control-Allow-Methods",
                    ", ".join(self.allow_methods),
                )
            )
            req_headers = _header_get(
                scope.headers, "access-control-request-headers"
            )
            acah = self._preflight_allow_headers(req_headers)
            if acah:
                headers.append(("Access-Control-Allow-Headers", acah))
            elif self.allow_headers_any:
                headers.append(("Access-Control-Allow-Headers", "*"))
            headers.append(("Access-Control-Max-Age", str(self.max_age)))
        elif self.expose_headers:
            headers.append(
                (
                    "Access-Control-Expose-Headers",
                    ", ".join(self.expose_headers),
                )
            )
        return headers

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        if scope.proto != "http":
            await self.app(scope, proto)
            return

        origin = _header_get(scope.headers, "origin")
        is_options = scope.method.upper() == HTTPMethod.OPTIONS.value
        is_preflight = is_options and _header_get(
            scope.headers, "access-control-request-method"
        )
        if is_preflight:
            if not self._origin_allowed(origin):
                proto.response_empty(HTTPStatus.BAD_REQUEST, [])
                return
            cors = self._cors_response_headers(scope, preflight=True)
            proto.response_empty(HTTPStatus.OK, cors)
            return

        allow_value = self._allow_origin_value(origin)
        if allow_value is None:
            await self.app(scope, proto)
            return

        cors = self._cors_response_headers(scope, preflight=False)
        wrapped = _HttpProtocolCORS(proto, cors)
        await self.app(scope, wrapped)
