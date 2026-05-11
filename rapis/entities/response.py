from http import HTTPStatus
from typing import Any

import msgspec

from rapis.types import HttpProtocol, Scope


class Response:
    def __init__(
        self, body: Any, status: HTTPStatus, headers: list[tuple[str, str]]
    ) -> None:
        self.body = body
        self.status = status
        self.headers = headers

    def __call__(self, _scope: Scope, proto: HttpProtocol) -> Any:
        proto.response_bytes(self.status, self.headers, self._parse_body())

    def _parse_body(self) -> bytes:
        return str(self.body).encode()


class JSONResponse(Response):
    def __call__(self, _scope: Scope, proto: HttpProtocol) -> Any:
        proto.response_bytes(
            self.status,
            self.headers + [("Content-type", "application/json")],
            self._parse_body(),
        )

    def _parse_body(self) -> bytes:
        return msgspec.json.encode(self.body)
