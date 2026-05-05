import inspect
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from http import HTTPStatus
from typing import (
    Any,
    Literal,
    get_args,
    get_type_hints,
)
from urllib.parse import parse_qsl

import msgspec
from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

from ._types import Query


@dataclass(frozen=True, slots=True)
class _ParamBinding:
    name: str
    source: Literal["query", "body"]
    type: type
    is_struct: bool
    default: Any | None = None


class Handler:
    def __init__(
        self, call: Callable[..., Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self.call = call
        self.status = status
        self.path_fields: frozenset[str] = frozenset()
        self.bindings: tuple[_ParamBinding, ...] = tuple(
            _extract_bindings(call)
        )

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> None:
        kwargs = await self.prepare(scope, proto)
        result = await self.call(**kwargs)
        await self.write_response(result, proto)

    async def prepare(
        self, scope: Scope, proto: RSGIHTTPProtocol
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

    async def write_response(
        self, result: Any, proto: RSGIHTTPProtocol
    ) -> None:
        payload = result
        if isinstance(result, msgspec.Struct | dict):
            payload = msgspec.json.encode(result)
        elif isinstance(result, str):
            payload = result.encode()

        proto.response_bytes(
            self.status, [("Content-Type", "application/json")], payload
        )


def _extract_bindings(
    call: Callable[..., Any],
) -> list[_ParamBinding]:
    sig = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)
    bindings: list[_ParamBinding] = []
    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        if ann is inspect.Parameter.empty:
            continue
        is_struct = isinstance(ann, type) and issubclass(ann, msgspec.Struct)
        if param.annotation.__name__ == Query.__name__:
            binding_source = "query"
            ann = next(iter(get_args(ann)), type(param.default))
            is_struct = issubclass(ann, msgspec.Struct)
        else:
            binding_source = "body"
        default = (
            param.default
            if param.default is not inspect.Parameter.empty
            else None
        )
        bindings.append(
            _ParamBinding(
                name=name,
                source=binding_source,
                type=ann,
                is_struct=is_struct,
                default=default,
            )
        )
    return bindings
