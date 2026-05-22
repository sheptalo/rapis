from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from re import Pattern

from rapis.entities.bindings import ParamBinding, ParamBindingSource


@dataclass(slots=True)
class Handler:
    call: Callable
    bindings: Sequence[ParamBinding] = field(default_factory=list)
    path_pattern: Pattern[str] | None = None

    def set_path_matching(
        self,
        *,
        pattern: Pattern[str] | None,
        fields: frozenset[str],
        types: dict[str, type],
    ) -> None:
        self.path_pattern = pattern
        rest = [
            b for b in self.bindings if b.source is not ParamBindingSource.path
        ]
        path_binds = [
            ParamBinding(
                name=name,
                source=ParamBindingSource.path,
                type=types[name],
                is_struct=False,
                default=None,
            )
            for name in sorted(fields)
        ]
        self.bindings = [*path_binds, *rest]
