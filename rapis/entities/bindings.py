from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ParamBindingSource(StrEnum):
    query = "query"
    body = "body"
    path = "path"


@dataclass(frozen=True, slots=True)
class ParamBinding:
    name: str
    source: str
    type: type
    is_struct: bool
    default: Any | None = None
