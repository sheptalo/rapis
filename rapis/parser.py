from collections.abc import Sequence

import msgspec

from rapis.types import Param, Parser, ParserCallable


class MsgSpecParser(Parser):
    def __init__(
        self, source: str = "query", fields: Sequence[str] | None = None
    ) -> None:
        if source not in ("query", "body"):
            raise ValueError(f"unknown source {source!r}")
        self.source = source
        self.fields = fields
        self.needs_body = source == "body"

    def build(self, params: list[Param]) -> ParserCallable:
        asdict = msgspec.structs.asdict
        if (
            self.source == "body"
            and len(params) == 1
            and issubclass(params[0].type, msgspec.Struct)
        ):
            (p,) = params
            decode = msgspec.json.Decoder(p.type).decode
            name, default = p.name, p.default
            if p.required:
                return lambda req: {name: decode(req.body)}
            return lambda req: {
                name: decode(req.body) if req.body else default
            }
        model = msgspec.defstruct(
            "Params",
            [
                (p.name, p.type) if p.required else (p.name, p.type, p.default)
                for p in params
            ],
            kw_only=True,
        )
        if self.source == "query":
            convert = msgspec.convert
            return lambda req: asdict(convert(req.query, model, strict=False))
        decode = msgspec.json.Decoder(model).decode
        return lambda req: asdict(decode(req.body or b"{}"))
