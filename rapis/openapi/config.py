import importlib.metadata as md
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OpenAPIConfig:
    title: str = "rapis"
    version: str = field(default_factory=lambda: md.version("rapis"))
    description: str | None = None
    openapi_version: str = "3.2.0"
    openapi_path: str = "/openapi.json"
    docs_path: str = "/docs"
