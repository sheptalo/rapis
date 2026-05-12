import inspect
from collections.abc import Callable
from typing import Any, get_args, get_type_hints
from urllib.parse import parse_qsl

import msgspec

from rapis.entities.bindings import ParamBinding, ParamBindingSource
from rapis.entities.handler import Handler
from rapis.types import HttpProtocol, Query, Scope


def extract_path_param_types(
    call: Callable[..., Any],
    path_fields: frozenset[str],
) -> dict[str, type]:
    if not path_fields:
        return {}
    sig = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)
    mapping: dict[str, type] = {}
    for name in path_fields:
        param = sig.parameters.get(name)
        if param is None:
            msg = (
                f"path includes parameter {name!r} but callable "
                f"{getattr(call, '__qualname__', repr(call))!r} "
                "has no matching parameter"
            )
            raise TypeError(msg)
        ann = hints.get(name, param.annotation)
        if ann is inspect.Parameter.empty:
            ann = str
        mapping[name] = ann
    return mapping


def extract_bindings(
    call: Callable[..., Any],
) -> list[ParamBinding]:
    sig = inspect.signature(call)
    hints = get_type_hints(call, include_extras=True)
    bindings: list[ParamBinding] = []
    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        if ann is inspect.Parameter.empty:
            continue
        is_struct = isinstance(ann, type) and issubclass(ann, msgspec.Struct)
        if param.annotation.__name__ == Query.__name__:
            binding_source = ParamBindingSource.query
            ann = next(iter(get_args(ann)), type(param.default))
            is_struct = issubclass(ann, msgspec.Struct)
        else:
            binding_source = ParamBindingSource.body
        default = (
            param.default
            if param.default is not inspect.Parameter.empty
            else None
        )
        bindings.append(
            ParamBinding(
                name=name,
                source=binding_source,
                type=ann,
                is_struct=is_struct,
                default=default,
            )
        )
    return bindings


async def parse_bindings(
    handler: Handler, scope: Scope, proto: HttpProtocol
) -> tuple[dict, dict]:
    kwargs: dict[str, Any] = {}
    errors = {}
    if not handler.bindings:
        return kwargs, errors
    decoded_body = {}
    query_dict = {}
    if scope.method in {"POST", "PUT", "PATCH"}:
        decoded_body = msgspec.json.decode(await proto())
    if scope.query_string:
        query_dict = dict(parse_qsl(scope.query_string))

    for b in handler.bindings:
        data_source = (
            query_dict
            if b.source == ParamBindingSource.query
            else decoded_body
        )
        data_source = (
            data_source.get(b.name) if not b.is_struct else data_source
        )
        if b.default is None and not data_source:
            errors["detail"] = "Missing Required field"
            continue
        try:
            value = msgspec.convert(
                data_source or b.default,
                b.type,
                strict=b.source is not ParamBindingSource.query,
            )
        except msgspec.ValidationError as e:
            errors["detail"] = str(e)
            break
        kwargs[b.name] = value
    return kwargs, errors
