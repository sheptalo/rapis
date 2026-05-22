import inspect
from collections.abc import Callable, Mapping
from typing import Any, get_args, get_origin, get_type_hints
from urllib.parse import parse_qsl

import msgspec

from rapis.abc.endpoint import Endpoint
from rapis.entities.bindings import ParamBinding, ParamBindingSource
from rapis.exceptions import DecodeError
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
        if get_origin(param.annotation) == Query:
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


def _binding_source_raw(
    b: ParamBinding,
    path_captures: Mapping[str, str],
    query_dict: dict[str, str],
    decoded_body: dict[str, Any],
) -> tuple[Any, bool]:  # TODO(): move from this to extensible variant
    if b.source is ParamBindingSource.path:
        return path_captures.get(b.name), False
    if b.source is ParamBindingSource.query:
        chunk = query_dict if b.is_struct else query_dict.get(b.name)
        return chunk, False
    chunk = decoded_body if b.is_struct else decoded_body.get(b.name)
    return chunk, True


async def parse_bindings(
    handler: Endpoint,
    scope: Scope,
    proto: HttpProtocol,
    path_captures: Mapping[str, str],
) -> tuple[dict[str, Any], dict]:
    kwargs: dict[str, Any] = {}
    errors: dict = {}
    if not handler.bindings:
        return kwargs, errors
    decoded_body: dict[str, Any] = {}
    query_dict: dict[str, str] = {}
    wants_body = any(
        b.source == ParamBindingSource.body for b in handler.bindings
    )
    if wants_body and scope.method in {"POST", "PUT", "PATCH"}:
        raw_body = await proto()
        if raw_body:
            try:
                decoded_body = msgspec.json.decode(raw_body)
            except msgspec.DecodeError as e:
                raise DecodeError from e
    wants_query = any(
        b.source == ParamBindingSource.query for b in handler.bindings
    )
    if wants_query and scope.query_string:
        query_dict = dict(parse_qsl(scope.query_string))

    for b in handler.bindings:
        raw, strict_convert = _binding_source_raw(
            b, path_captures, query_dict, decoded_body
        )

        if b.default is None and not raw and raw != 0 and raw is not False:
            errors["detail"] = "Missing Required field"
            continue
        try:
            value = msgspec.convert(
                raw if raw is not None else b.default,
                b.type,
                strict=strict_convert,
            )
        except msgspec.ValidationError as e:
            errors["detail"] = str(e)
            break
        kwargs[b.name] = value
    return kwargs, errors
