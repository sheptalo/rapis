from collections.abc import Awaitable, Callable, Mapping, Sequence
from re import Pattern
from typing import Any, Protocol

from rapis.entities.bindings import ParamBinding


class Endpoint(Protocol):
    call: Callable[..., Awaitable[Any]]
    bindings: Sequence[ParamBinding]
    path_types: Mapping[str, type]
    path_pattern: Pattern[str] | None
