import re
from re import Pattern

import msgspec

from rapis.entities.handler import Handler
from rapis.exceptions import ValidationError

_SEGMENT_PARAM = re.compile(r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$")


def path_params(handler: Handler, path: str) -> dict:
    if handler.path_pattern is None:
        return {}
    m = handler.path_pattern.fullmatch(path)
    if not m:
        return {}
    raw = m.groupdict()
    out: dict = {}
    for name, value in raw.items():
        typ = handler.path_types[name]
        try:
            out[name] = msgspec.convert(value, typ, strict=False)
        except msgspec.ValidationError as e:
            raise ValidationError(errors={"detail": str(e)}) from e
    return out


def compile_path_pattern(
    path: str,
) -> tuple[Pattern[str] | None, frozenset[str]]:
    if "{" not in path:
        return None, frozenset()

    rooted = path if path.startswith("/") else f"/{path}"
    segments = [p for p in rooted.split("/") if p != ""]

    names_seen: list[str] = []
    escaped_parts: list[str] = []
    for part in segments:
        m = _SEGMENT_PARAM.fullmatch(part)
        if m:
            name = m.group(1)
            if name in names_seen:
                msg = f"duplicate path parameter {name!r} in route {path!r}"
                raise ValueError(msg)
            names_seen.append(name)
            escaped_parts.append(f"(?P<{name}>[^/]+)")
        else:
            escaped_parts.append(re.escape(part))

    regex_str = "^/" + "/".join(escaped_parts) + "$"
    return re.compile(regex_str), frozenset(names_seen)


def normalize_route_path(path: str) -> str:
    return path if path.startswith("/") or path == "" else f"/{path}"
