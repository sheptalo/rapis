import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import (
    Any,
    Literal,
    get_args,
    get_type_hints,
)

import msgspec

from rapis.types import Query


@dataclass(frozen=True, slots=True)
class _ParamBinding:
    name: str
    source: Literal["query", "body"]
    type: type
    is_struct: bool
    default: Any | None = None


def extract_bindings(
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
