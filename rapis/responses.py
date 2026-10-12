from collections.abc import Mapping
from typing import Any

import msgspec

from rapis.exceptions import HTTPError
from rapis.types import Headers, Request, Response

encode = msgspec.json.Encoder().encode
_json_header = ("content-type", "application/json")


def json_response(
    body: Mapping[str, Any], status: int = 200, headers: Headers | None = None
) -> Response:
    headers = [_json_header, *headers] if headers else [_json_header]
    return Response(status, headers, encode(body))


def http_error(exc: HTTPError, _req: Request) -> Response:
    return json_response({"detail": exc.detail}, exc.status)


def validation_error(exc: msgspec.ValidationError, _req: Request) -> Response:
    return json_response({"detail": str(exc)}, 400)


def decode_error(_exc: msgspec.DecodeError, _req: Request) -> Response:
    return json_response({"detail": "JSON Decode Error"}, 400)
