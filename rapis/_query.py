from urllib.parse import parse_qsl


def parse_query(qs: str, /) -> dict[str, str]:
    if "%" in qs or "+" in qs:
        return dict(parse_qsl(qs, keep_blank_values=True))
    out: dict[str, str] = {}
    for pair in qs.split("&"):
        if pair:
            key, _, value = pair.partition("=")
            out[key] = value
    return out
