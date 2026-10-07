import asyncio
import random
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from urllib.parse import parse_qsl

import pytest

from rapis import App, BuildError, Router
from rapis._query import parse_query as python_parse_query
from rapis.types import parse_query

TOKENS = [
    *"ab1=&;%+ /2F?#xAf9",
    *("é", "€", "😀", "\ud800"),
    *("%C3", "%A9", "%E2%82", "%FF", "%D0%BF", "%ED%A0%80", "%zz", "%4", "%%"),
]


@pytest.mark.parametrize(
    "parse", [python_parse_query, parse_query], ids=["python", "rapis"]
)
def test_parse_query_matches_parse_qsl(
    parse: Callable[[str], dict[str, str]],
) -> None:
    rnd = random.Random(0)
    cases = [
        "".join(rnd.choices(TOKENS, k=rnd.randint(0, 30)))
        for _ in range(20_000)
    ]
    cases.append("q=" + "%D0%BF" * 100)  # длиннее стекового буфера в C
    for qs in cases:
        expected = dict(parse_qsl(qs, keep_blank_values=True))
        got = parse(qs)
        assert got == expected, qs
        assert list(got) == list(expected), qs


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


def call(app: App, method: str, path: str) -> tuple[int, bytes]:
    proto = Proto()
    scope = SimpleNamespace(
        method=method, path=path, query_string="", headers={}
    )
    asyncio.run(app.__rsgi__(scope, proto))
    return proto.status, proto.body


def test_dynamic_routes_first_registered_wins() -> None:
    router = Router()

    @router.get("/a/{x}/b")
    async def first(x: str) -> list[str]:
        return ["first", x]

    @router.get("/a/c/{y}")
    async def second(y: str) -> list[str]:
        return ["second", y]

    @router.get("/files/{name}.txt")
    async def text(name: str) -> list[str]:
        return ["text", name]

    @router.get("/files/{name}")
    async def file(name: str) -> list[str]:
        return ["file", name]

    @router.get("/u/{a}/{b}")
    async def pair(a: str, b: str) -> list[str]:
        return ["pair", a, b]

    app = App(router)
    assert call(app, "GET", "/a/c/b") == (200, b'["first","c"]')
    assert call(app, "GET", "/a/c/d") == (200, b'["second","d"]')
    assert call(app, "GET", "/files/doc.txt") == (200, b'["text","doc"]')
    assert call(app, "GET", "/files/doc") == (200, b'["file","doc"]')
    assert call(app, "GET", "/u/1/2") == (200, b'["pair","1","2"]')
    assert call(app, "POST", "/u/1/2")[0] == 405
    assert call(app, "GET", "/nope")[0] == 404


def test_grouped_routes_keep_registration_order() -> None:
    # от 32 динамических маршрутов поиск идёт по группам
    router = Router(prefix="/api")

    @router.get("/{lang}/home")
    async def home(lang: str) -> list[str]:
        return ["home", lang]

    def item(i: int) -> Callable[[str], Awaitable[list[str]]]:
        async def handler(x: str) -> list[str]:
            return [f"r{i}", x]

        return handler

    for i in range(40):
        router.get(f"/r{i}/{{x}}")(item(i))

    app = App(router)
    assert call(app, "GET", "/api/r7/home") == (200, b'["home","r7"]')
    assert call(app, "GET", "/api/r7/42") == (200, b'["r7","42"]')
    assert call(app, "GET", "/api/r39/5") == (200, b'["r39","5"]')
    assert call(app, "GET", "/api/zz/home") == (200, b'["home","zz"]')
    assert call(app, "GET", "/api/zz/42")[0] == 404
    assert call(app, "GET", "/other/r7/42")[0] == 404


def test_repeated_path_param_is_rejected() -> None:
    router = Router()

    @router.get("/a/{x}/{x}")
    async def handler(x: str) -> str:
        return x

    with pytest.raises(BuildError):
        App(router).build()
