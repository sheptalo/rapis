from collections.abc import Callable
from contextlib import suppress
from http import HTTPStatus
from typing import (
    Any,
)
from urllib.parse import parse_qsl

import msgspec

from rapis.types import HttpProtocol, Scope
from rapis.utils import extract_bindings


class Handler:
    def __init__(
        self, call: Callable[..., Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self.call = call
        self.status = status
        self.path_fields: frozenset[str] = frozenset()
        self.bindings = extract_bindings(call)

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        kwargs = await self.prepare(scope, proto)
        result = await self.call(**kwargs)
        await self.write_response(result, proto)

    async def prepare(
        self, scope: Scope, proto: HttpProtocol
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        decoded_body = {}
        if scope.method in {"POST", "PUT", "PATCH"}:
            with suppress(msgspec.DecodeError):
                decoded_body = msgspec.json.decode(await proto())
        query_dict = {}
        if scope.query_string:
            query_dict = dict(parse_qsl(scope.query_string))

        for b in self.bindings:
            if not b.is_struct:
                if b.source == "query":
                    kwargs[b.name] = b.type(query_dict.get(b.name, b.default))
                else:
                    kwargs[b.name] = b.type(
                        decoded_body.get(b.name, b.default)
                    )
            else:
                if b.source == "query":
                    kwargs[b.name] = msgspec.convert(
                        query_dict or b.default, b.type
                    )
                else:
                    kwargs[b.name] = msgspec.convert(
                        decoded_body or b.default, type=b.type
                    )
        return kwargs

    async def write_response(self, result: Any, proto: HttpProtocol) -> None:
        payload = result
        if isinstance(result, msgspec.Struct | dict):
            payload = msgspec.json.encode(result)
        elif isinstance(result, str):
            payload = result.encode()
        else:
            payload = str(result).encode()

        proto.response_bytes(
            self.status, [("Content-Type", "application/json")], payload
        )
