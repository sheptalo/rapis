from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from re import Pattern


@dataclass
class Handler:
    call: Callable
    bindings: list
    status: HTTPStatus
    path_pattern: Pattern[str] | None = None
    path_fields: frozenset[str] = field(default_factory=frozenset)
    path_types: dict[str, type] = field(default_factory=dict)
    is_request_response: bool = False

    def set_path_matching(
        self,
        *,
        pattern: Pattern[str] | None,
        fields: frozenset[str],
        types: dict[str, type],
    ) -> None:
        self.path_pattern = pattern
        self.path_fields = fields
        self.path_types = types
