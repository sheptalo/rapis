import re
from typing import Literal
from urllib.parse import unquote

_PARAM_RE = re.compile(r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$")

type _SegKind = Literal["literal", "param"]


def _split_request_path(request_path: str) -> list[str]:
    raw = (request_path or "").split("?", 1)[0].strip()
    if not raw or raw == "/":
        return []
    return [unquote(s) for s in raw.strip("/").split("/") if s]


def _split_template_path(template: str) -> list[str]:
    raw = (template or "").strip()
    if not raw or raw == "/":
        return []
    return [s for s in raw.strip("/").split("/") if s]


def compile_route_path(
    template: str,
) -> tuple[list[tuple[_SegKind, str]], frozenset[str]]:
    """Return compiled segments and the set of path parameter names."""
    out: list[tuple[_SegKind, str]] = []
    names: set[str] = set()
    for seg in _split_template_path(template):
        m = _PARAM_RE.fullmatch(seg)
        if m:
            name = m.group(1)
            out.append(("param", name))
            names.add(name)
        else:
            if "{" in seg or "}" in seg:
                msg = f"Invalid route segment {seg!r} in template {template!r}"
                raise ValueError(msg)
            out.append(("literal", seg))
    return out, frozenset(names)


def match_route_path(
    compiled: list[tuple[_SegKind, str]], request_path: str
) -> dict[str, str] | None:
    req_segs = _split_request_path(request_path)
    if len(req_segs) != len(compiled):
        return None
    params: dict[str, str] = {}
    for (kind, val), rseg in zip(compiled, req_segs, strict=True):
        if kind == "literal":
            if val != rseg:
                return None
        else:
            params[val] = rseg
    return params
