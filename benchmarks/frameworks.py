# /// script
# requires-python = ">=3.12"
# dependencies = ["rapis", "blacksheep", "litestar", "fastapi"]
#
# [tool.uv.sources]
# rapis = { path = "..", editable = true }
# ///
"""Per-request latency of rapis, BlackSheep, Litestar and FastAPI.

In-process, no server: see benchmarks/README.md for the method.

    uv run benchmarks/frameworks.py
    ROUNDS=40 N=20000 uv run benchmarks/frameworks.py
"""

import asyncio
import gc
import os
import random
import statistics
import sys
import time
from importlib.metadata import version
from types import SimpleNamespace

from blacksheep import Application
from blacksheep.server.routing import Router as BSRouter
from fastapi import FastAPI
from litestar import Litestar, get

import rapis
import rapis._query
import rapis.types

ROUNDS = int(os.environ.get("ROUNDS", "20"))
N = int(os.environ.get("N", "10000"))
WARM = 500  # после чужого варианта кеши процессора холодные
Q6 = "a=1&b=2&c=3&d=4&e=5&f=6"
QENC = "q=%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82+%D0%BC%D0%B8%D1%80&page=2"
SCENARIOS = [  # название, приложение, путь ({id} — свой у каждого запроса), query
    ("empty, 204", "base", "/", ""),
    ("path, 1 dynamic route", "base", "/items/{id}", ""),
    ("path, 50 dynamic routes", "dyn50", "/r49/{id}", ""),
    ("path, 200 dynamic routes", "dyn200", "/r199/{id}", ""),
    ("query, 2 params", "base", "/query", "skip=256&limit=10"),
    ("query, 6 params", "base", "/query6", Q6),
    ("query, %-encoded", "base", "/search", QENC),
    ("empty + 1 middleware", "mw1", "/", ""),
    ("empty + 3 middleware", "mw3", "/", ""),
    ("empty + 5 middleware", "mw5", "/", ""),
]
ASGI = ("BlackSheep", "Litestar", "FastAPI")
VARIANTS = ("rapis", "rapis (no C)", *ASGI)

# rapis выбирает parse_query при импорте; вариант «no C» на время своих
# пачек подменяет его Python-версией
NATIVE_QUERY = rapis.types.parse_query
PYTHON_QUERY = rapis._query.parse_query


# --- rapis -------------------------------------------------------------------
class Pass:
    async def __call__(self, handler, request):
        return await handler(request)


def rapis_apps() -> dict:
    base = rapis.Router()

    @base.get("/")
    async def empty() -> None: ...

    @base.get("/items/{item_id}")
    async def item(item_id: int) -> None: ...

    @base.get("/query")
    @rapis.MsgSpecParser()
    async def query(skip: int = 0, limit: int = 10) -> None: ...

    @base.get("/query6")
    @rapis.MsgSpecParser()
    async def query6(a: int = 0, b: int = 0, c: int = 0, d: int = 0,
                     e: int = 0, f: int = 0) -> None: ...

    @base.get("/search")
    @rapis.MsgSpecParser()
    async def search(q: str = "", page: int = 1) -> None: ...

    routers = {"base": base}
    for k in (50, 200):
        routers[f"dyn{k}"] = dyn = rapis.Router()
        for i in range(k):
            @dyn.get(f"/r{i}/{{item_id}}")
            async def h(item_id: int) -> None: ...

    for k in (1, 3, 5):
        routers[f"mw{k}"] = mw = rapis.Router()
        mw.middlewares.extend(Pass() for _ in range(k))
        mw.get("/")(empty)
    apps = {key: rapis.App(router) for key, router in routers.items()}
    for app in apps.values():
        app.build()
    return apps


class Proto:
    def __init__(self) -> None:
        self.status = None

    async def __call__(self) -> bytes:
        return b""

    def response_bytes(self, status, headers, body) -> None:
        self.status = status


def rsgi_caller(app):
    proto, rsgi = Proto(), app.__rsgi__

    async def call(scope) -> None:
        await rsgi(scope, proto)

    return call, lambda: proto.status


# --- BlackSheep ----------------------------------------------------------------
async def bs_pass(request, handler):
    return await handler(request)


def bs_apps() -> dict:
    base = Application(router=BSRouter())

    @base.router.get("/")
    async def empty() -> None: ...

    @base.router.get("/items/{item_id}")
    async def item(item_id: int) -> None: ...

    @base.router.get("/query")
    async def query(skip: int = 0, limit: int = 10) -> None: ...

    @base.router.get("/query6")
    async def query6(a: int = 0, b: int = 0, c: int = 0, d: int = 0,
                     e: int = 0, f: int = 0) -> None: ...

    @base.router.get("/search")
    async def search(q: str = "", page: int = 1) -> None: ...

    apps = {"base": base}
    for k in (50, 200):
        apps[f"dyn{k}"] = app = Application(router=BSRouter())
        for i in range(k):
            @app.router.get(f"/r{i}/{{item_id}}")
            async def h(item_id: int) -> None: ...

    for k in (1, 3, 5):
        apps[f"mw{k}"] = app = Application(router=BSRouter())
        app.middlewares.extend(bs_pass for _ in range(k))
        app.router.get("/")(empty)
    return apps


# --- Litestar ------------------------------------------------------------------
def pass_asgi(app):  # самый лёгкий вид middleware в Litestar
    async def middleware(scope, receive, send):
        await app(scope, receive, send)

    return middleware


def ls_apps() -> dict:
    def base_handlers() -> list:
        @get("/", status_code=204)
        async def empty() -> None: ...

        @get("/items/{item_id:int}", status_code=204)
        async def item(item_id: int) -> None: ...

        @get("/query", status_code=204)
        async def query(skip: int = 0, limit: int = 10) -> None: ...

        @get("/query6", status_code=204)
        async def query6(a: int = 0, b: int = 0, c: int = 0, d: int = 0,
                         e: int = 0, f: int = 0) -> None: ...

        @get("/search", status_code=204)
        async def search(q: str = "", page: int = 1) -> None: ...

        return [empty, item, query, query6, search]

    def dyn_handlers(k: int) -> list:
        out = []
        for i in range(k):
            async def h(item_id: int) -> None: ...
            out.append(get(f"/r{i}/{{item_id:int}}", status_code=204,
                           name=f"r{i}")(h))
        return out

    def empty_handler() -> list:
        @get("/", status_code=204)
        async def empty() -> None: ...

        return [empty]

    apps = {"base": Litestar(base_handlers(), openapi_config=None)}
    for k in (50, 200):
        apps[f"dyn{k}"] = Litestar(dyn_handlers(k), openapi_config=None)
    for k in (1, 3, 5):
        apps[f"mw{k}"] = Litestar(empty_handler(), openapi_config=None,
                                  middleware=[pass_asgi] * k)
    return apps


# --- FastAPI -------------------------------------------------------------------
class PassASGI:  # чистая ASGI-middleware, самый быстрый вид в FastAPI
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        await self.app(scope, receive, send)


def fa_apps() -> dict:
    def new() -> FastAPI:  # без /docs и /openapi.json, как и у остальных
        return FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    base = new()

    @base.get("/", status_code=204)
    async def empty() -> None: ...

    @base.get("/items/{item_id}", status_code=204)
    async def item(item_id: int) -> None: ...

    @base.get("/query", status_code=204)
    async def query(skip: int = 0, limit: int = 10) -> None: ...

    @base.get("/query6", status_code=204)
    async def query6(a: int = 0, b: int = 0, c: int = 0, d: int = 0,
                     e: int = 0, f: int = 0) -> None: ...

    @base.get("/search", status_code=204)
    async def search(q: str = "", page: int = 1) -> None: ...

    apps = {"base": base}
    for k in (50, 200):
        apps[f"dyn{k}"] = app = new()
        for i in range(k):
            async def h(item_id: int) -> None: ...
            app.get(f"/r{i}/{{item_id}}", status_code=204)(h)
    for k in (1, 3, 5):
        apps[f"mw{k}"] = app = new()
        for _ in range(k):
            app.add_middleware(PassASGI)
        app.get("/", status_code=204)(empty)
    return apps


# --- ASGI: каждый запрос получает свой scope, как от сервера ---------------------
def asgi_scope(path: str, qs: str) -> dict:
    return {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path, "raw_path": path.encode(), "root_path": "",
        "query_string": qs.encode(), "headers": [(b"host", b"127.0.0.1")],
        "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 8000),
    }


def asgi_caller(app):
    message = {"type": "http.request", "body": b"", "more_body": False}
    status = {}

    async def receive() -> dict:
        return message

    async def send(m: dict) -> None:
        if m["type"] == "http.response.start":
            status["s"] = m["status"]

    async def call(template) -> None:
        scope = template.copy()
        scope["state"] = {}
        await app(scope, receive, send)

    return call, lambda: status.get("s")


def scopes(path: str, qs: str) -> tuple[list, list]:
    # разные id, как в настоящем трафике: иначе отвечает кеш маршрутов
    # (у BlackSheep lru_cache на 1200 путей), а не сама маршрутизация
    if "{id}" not in path:
        return ([SimpleNamespace(method="GET", path=path, query_string=qs,
                                 headers={})] * N, [asgi_scope(path, qs)] * N)
    paths = [path.format(id=i) for i in range(N)]
    return ([SimpleNamespace(method="GET", path=p, query_string=qs,
                             headers={}) for p in paths],
            [asgi_scope(p, qs) for p in paths])


# --- замер ---------------------------------------------------------------------
async def noop(_scope) -> None:
    pass


async def scope_copy(template) -> None:  # копия scope без приложения
    scope = template.copy()
    scope["state"] = {}


async def batch(fn, scopes: list) -> float:
    for scope in scopes[:WARM]:
        await fn(scope)
    pc = time.perf_counter_ns
    t0 = pc()
    for scope in scopes:
        await fn(scope)
    return (pc() - t0) / len(scopes)


def use(variant: str) -> None:
    rapis.types.parse_query = (
        PYTHON_QUERY if variant == "rapis (no C)" else NATIVE_QUERY
    )


def table(title: str, rows: list, fmt) -> None:
    print(f"\n{title:26}" + "".join(f"{v:>13}" for v in VARIANTS))
    for name, cells in rows:
        print(f"{name:26}" + "".join(f"{fmt(cells[v]):>13}" for v in VARIANTS))


async def main() -> None:
    print(f"Python {sys.version.split()[0]}, " + ", ".join(
        f"{p} {version(p)}" for p in
        ("msgspec", "blacksheep", "litestar", "fastapi", "starlette")))
    if NATIVE_QUERY is PYTHON_QUERY:
        print("rapis C module is not built: both rapis columns are the same")
    rapis_built = rapis_apps()
    built = {"rapis": rapis_built, "rapis (no C)": rapis_built,
             "BlackSheep": bs_apps(), "Litestar": ls_apps(),
             "FastAPI": fa_apps()}
    for app in built["BlackSheep"].values():
        await app.start()
    scenarios = []
    for name, key, path, qs in SCENARIOS:
        rsgi_scopes, asgi_scopes = scopes(path, qs)
        runs = {v: (*(asgi_caller if v in ASGI else rsgi_caller)(
            built[v][key]), asgi_scopes if v in ASGI else rsgi_scopes)
            for v in VARIANTS}
        scenarios.append((name, rsgi_scopes, asgi_scopes, runs))
    for _, _, _, runs in scenarios:  # прогрев и проверка, что все отвечают 204
        for v, (call, status, sc) in runs.items():
            use(v)
            await batch(call, sc)
            if status() != 204:
                print(f"  {v}: status {status()} instead of 204")
    # объекты, созданные при сборке приложений, не должны попадать в полную
    # сборку мусора посреди замера
    gc.collect()
    gc.freeze()

    best, ratios = [], []
    rng = random.Random(0)
    for name, rsgi_scopes, asgi_scopes, runs in scenarios:
        res = {v: [] for v in VARIANTS}
        base, base_asgi = [], []
        for _ in range(ROUNDS):
            base.append(await batch(noop, rsgi_scopes))
            base_asgi.append(await batch(scope_copy, asgi_scopes))
            for v in rng.sample(VARIANTS, len(VARIANTS)):
                use(v)
                call, _, sc = runs[v]
                res[v].append(await batch(call, sc))
        own = {v: min(base_asgi if v in ASGI else base) for v in VARIANTS}
        net = {v: [t - own[v] for t in res[v]] for v in VARIANTS}
        best.append((name, {v: min(net[v]) for v in VARIANTS}))
        ratios.append((name, {
            v: statistics.median(x / y for x, y in zip(net[v], net["rapis"]))
            for v in VARIANTS
        }))
        print(f"  {name}: done", file=sys.stderr)
    use("rapis")

    table("ns per request, best", best, lambda x: f"{x:.0f}")
    table("relative to rapis", ratios, lambda x: f"{x:.2f}")


asyncio.run(main())
