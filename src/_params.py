from typing import Any

from ._types import Query as TQuery


def query(default: Any | None = None) -> Any:
    return TQuery(default)
