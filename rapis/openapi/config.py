import importlib.metadata as md
from dataclasses import dataclass, field

from rapis.openapi.constants import OPENAPI_VERSION


@dataclass(frozen=True, slots=True)
class OpenAPIConfig:
    title: str = "rapis"
    version: str = field(default_factory=lambda: md.version("rapis"))
    description: str | None = None
    openapi_version: str = OPENAPI_VERSION
    openapi_path: str = "/openapi.json"
    docs_path: str = "/docs"
