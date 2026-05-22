import re
from re import Pattern

_SEGMENT_PARAM = re.compile(r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$")


def path_captures(pattern: Pattern[str] | None, path: str) -> dict[str, str]:
    m = pattern.fullmatch(path) if pattern else None
    return dict(m.groupdict()) if m else {}


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
