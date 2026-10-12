import asyncio
import json
from types import SimpleNamespace

import msgspec
import pytest

from rapis import App, Router

TOKENS = [
    "0",
    "00",
    "007",
    "7",
    "42",
    "99999999999999999999",
    "-3",
    "-0",
    "+7",
    " 7",
    "7 ",
    "1_000",
    "7.0",
    "1e3",
    "abc",
    "١٢",  # арабско-индийские цифры
    "７",  # полноширинная цифра
    "²",  # надстрочный индекс, isdigit() = True
]


class Proto:
    def __init__(self) -> None:
        self.status = 0
        self.body = b""

    async def __call__(self) -> bytes:
        return b""

    def response_bytes(
        self, status: int, _headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self.status, self.body = status, body


def call(app: App, path: str) -> tuple[int, bytes]:
    proto = Proto()
    scope = SimpleNamespace(
        method="GET", path=path, query_string="", headers={}
    )
    asyncio.run(app.__rsgi__(scope, proto))
    return proto.status, proto.body


@pytest.mark.parametrize("raw", TOKENS)
def test_int_path_param_matches_msgspec(raw: str) -> None:
    router = Router()

    @router.get("/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"v": item_id}

    oracle = msgspec.defstruct("PathParams", [("item_id", int)], kw_only=True)
    status, body = call(App(router), f"/items/{raw}")
    try:
        value = msgspec.convert({"item_id": raw}, oracle, strict=False)
    except msgspec.ValidationError as exc:
        assert status == 400
        assert json.loads(body) == {"detail": str(exc)}
    else:
        assert status == 200
        assert json.loads(body) == {"v": value.item_id}


@pytest.mark.parametrize(
    ("a", "b"), [("7", "x"), ("007", "x"), ("x", "y"), ("-1", "y")]
)
def test_mixed_path_params_match_msgspec(a: str, b: str) -> None:
    router = Router()

    @router.get("/pair/{a}/{b}")
    async def pair(a: int, b: str) -> dict[str, object]:
        return {"a": a, "b": b}

    oracle = msgspec.defstruct(
        "PathParams", [("a", int), ("b", str)], kw_only=True
    )
    status, body = call(App(router), f"/pair/{a}/{b}")
    try:
        value = msgspec.convert({"a": a, "b": b}, oracle, strict=False)
    except msgspec.ValidationError as exc:
        assert status == 400
        assert json.loads(body) == {"detail": str(exc)}
    else:
        assert status == 200
        assert json.loads(body) == {"a": value.a, "b": value.b}
