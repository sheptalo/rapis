import inspect
from collections.abc import Callable
from contextlib import suppress
from contextvars import ContextVar, Token
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Literal, get_type_hints
from urllib.parse import parse_qsl

import msgspec
from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope
from msgspec import DecodeError, Struct

from ._types import Query

_path_params: ContextVar[dict[str, str] | None] = ContextVar(
    "_path_params", default=None
)


def path_params_context_token(
    params: dict[str, str],
) -> Token[dict[str, str] | None]:
    return _path_params.set(params)


def reset_path_params_context(token: Token[dict[str, str] | None]) -> None:
    _path_params.reset(token)


def _current_path_params() -> dict[str, str]:
    v = _path_params.get()
    return v if v is not None else {}


@dataclass(frozen=True, slots=True)
class _ParamBinding:
    name: str
    source: Literal["path", "query", "body"]
    type: type
    is_struct: bool


class Handler:
    def __init__(
        self, call: Callable[..., Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self.call = call
        self.status = status
        self.path_fields: frozenset[str] = frozenset()
        self.bindings: tuple[_ParamBinding, ...] = tuple(
            _extract_bindings(call, frozenset())
        )

    def set_path_fields(self, path_fields: frozenset[str]) -> None:
        self.path_fields = path_fields
        self.bindings = tuple(_extract_bindings(self.call, path_fields))

    async def __call__(self, scope: Scope, proto: RSGIHTTPProtocol) -> None:
        kwargs = await self.prepare(scope, proto)
        result = await self.call(**kwargs)
        await self.write_response(result, proto)

    async def prepare(
        self, scope: Scope, proto: RSGIHTTPProtocol
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        decoded_body = {}
        with suppress(DecodeError):
            decoded_body = msgspec.json.decode(await proto())
        query_dict = dict(parse_qsl(scope.query_string))
        path_ctx = _current_path_params()

        for b in self.bindings:
            if not b.is_struct:
                if b.source == "path":
                    kwargs[b.name] = b.type(path_ctx[b.name])
                elif b.source == "query":
                    kwargs[b.name] = b.type(query_dict.get(b.name))
                else:
                    kwargs[b.name] = b.type(decoded_body.get(b.name))
            elif b.source == "path":
                fields = getattr(b.type, "__struct_fields__", ())
                subset = {k: path_ctx[k] for k in fields if k in path_ctx}
                kwargs[b.name] = msgspec.convert(subset, type=b.type)
            elif b.source == "query":
                kwargs[b.name] = msgspec.convert(query_dict, b.type)
            else:
                kwargs[b.name] = msgspec.convert(decoded_body, type=b.type)
        return kwargs

    async def write_response(
        self, result: Any, proto: RSGIHTTPProtocol
    ) -> None:
        payload = result
        if isinstance(result, Struct | dict):
            payload = msgspec.json.encode(result)
        elif isinstance(result, str):
            payload = result.encode()

        proto.response_bytes(
            self.status, [("Content-Type", "application/json")], payload
        )


def _extract_bindings(
    call: Callable[..., Any], path_fields: frozenset[str]
) -> list[_ParamBinding]:
    sig = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)
    bindings: list[_ParamBinding] = []

    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        if ann is inspect.Parameter.empty:
            continue
        if not isinstance(ann, type):
            continue
        is_struct = issubclass(ann, Struct)
        if name in path_fields:
            binding_source = "path"
        elif isinstance(param.default, Query):
            binding_source = "query"
        else:
            binding_source = "body"
        bindings.append(
            _ParamBinding(
                name=name, source=binding_source, type=ann, is_struct=is_struct
            )
        )

    return bindings
