import asyncio
import json
import logging
from types import SimpleNamespace

import msgspec
import pytest

from rapis import App, CORSMiddleware, MsgSpecParser, Router
from rapis.exceptions import HTTPError
from rapis.responses import json_response
from rapis.types import Handler, Request, Response


class Proto:
    def __init__(self, body: bytes = b"") -> None:
        self.body = body
        self.status = 0
        self.headers: list[tuple[str, str]] = []
        self.payload = b""

    async def __call__(self) -> bytes:
        return self.body

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self.status, self.headers, self.payload = status, headers, body


def call(
    app: App,
    method: str = "GET",
    path: str = "/",
    *,
    query: str = "",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> Proto:
    proto = Proto(body)
    scope = SimpleNamespace(
        method=method,
        path=path,
        query_string=query,
        headers=headers or {},
    )
    asyncio.run(app.__rsgi__(scope, proto))
    return proto


def test_none_return_is_204() -> None:
    router = Router()

    @router.get("/")
    async def handler() -> None: ...

    proto = call(App(router))
    assert (proto.status, proto.headers, proto.payload) == (204, [], b"")


def test_dict_return_is_json_200() -> None:
    router = Router()

    @router.get("/")
    async def handler() -> dict[str, str]:
        return {"ok": "true"}

    proto = call(App(router))
    assert proto.status == 200
    assert proto.headers == [("content-type", "application/json")]
    assert proto.payload == b'{"ok":"true"}'


def test_int_path_param_is_converted_and_checked() -> None:
    router = Router()

    @router.get("/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    app = App(router)
    assert call(app, path="/items/7").payload == b'{"id":7}'
    proto = call(app, path="/items/abc")
    assert proto.status == 400
    assert isinstance(json.loads(proto.payload)["detail"], str)


def test_unknown_path_is_404() -> None:
    proto = call(App(Router()), path="/nope")
    assert (proto.status, proto.payload) == (404, b'{"detail":"Not Found"}')


def test_method_not_allowed_lists_allowed_methods() -> None:
    router = Router()

    @router.get("/x")
    async def get_x() -> None: ...

    @router.post("/x")
    async def post_x() -> None: ...

    proto = call(App(router), "DELETE", "/x")
    assert (proto.status, proto.headers) == (405, [("allow", "GET, POST")])


def test_star_method_accepts_any_method() -> None:
    router = Router()

    @router.route("/any")
    async def any_method() -> None: ...

    assert call(App(router), "PATCH", "/any").status == 204


def test_query_validation_error_is_400() -> None:
    router = Router()

    @router.get("/")
    @MsgSpecParser()
    async def handler(q: int = 0) -> None: ...

    proto = call(App(router), query="q=abc")
    assert proto.status == 400
    assert isinstance(json.loads(proto.payload)["detail"], str)


class Item(msgspec.Struct):
    name: str


def test_bad_json_body_is_400() -> None:
    router = Router()

    @router.post("/")
    @MsgSpecParser(source="body")
    async def create(item: Item) -> None: ...

    proto = call(App(router), "POST", "/", body=b"{")
    assert (proto.status, proto.payload) == (
        400,
        b'{"detail":"JSON Decode Error"}',
    )


def test_http_error_becomes_its_status_and_detail() -> None:
    router = Router()

    @router.get("/")
    async def handler() -> None:
        raise HTTPError(409, "conflict")

    proto = call(App(router))
    assert (proto.status, proto.payload) == (409, b'{"detail":"conflict"}')


def test_custom_exception_handler_matches_by_mro() -> None:
    router = Router()

    @router.get("/")
    async def handler() -> None:
        raise KeyError("missing")

    def lookup_error(_exc: LookupError, _req: Request) -> Response:
        return json_response({"detail": "custom"}, 422)

    app = App(router, exception_handlers={LookupError: lookup_error})
    proto = call(app)
    assert (proto.status, proto.payload) == (422, b'{"detail":"custom"}')


def test_unhandled_error_is_500_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    router = Router()

    @router.get("/")
    async def handler() -> None:
        raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR, logger="rapis"):
        proto = call(App(router))

    assert (proto.status, proto.payload) == (500, b"Internal Server Error")
    [record] = [r for r in caplog.records if r.name == "rapis"]
    assert record.getMessage() == "unhandled error"
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError


def test_route_middleware_errors_are_mapped() -> None:
    class Forbid:
        async def __call__(
            self,
            handler: Handler,  # noqa: ARG002
            request: Request,  # noqa: ARG002
        ) -> Response:
            raise HTTPError(403, "no")

    router = Router()
    router.middlewares.append(Forbid())

    @router.get("/")
    async def handler() -> None: ...

    proto = call(App(router))
    assert (proto.status, proto.payload) == (403, b'{"detail":"no"}')


class Raise:
    async def __call__(
        self,
        handler: Handler,  # noqa: ARG002
        request: Request,  # noqa: ARG002
    ) -> Response:
        raise HTTPError(403, "no")


class Deny:
    async def __call__(
        self,
        handler: Handler,  # noqa: ARG002
        request: Request,  # noqa: ARG002
    ) -> Response:
        return json_response({"detail": "no"}, 401)


class Crash:
    async def __call__(
        self,
        handler: Handler,  # noqa: ARG002
        request: Request,  # noqa: ARG002
    ) -> Response:
        raise RuntimeError("boom")


def test_outer_middleware_raised_error_is_mapped_without_cors() -> None:
    # контракт: мидлварь возвращает Response; бросок мимо CORS даёт статус
    # из маппинга на входе, но CORS-заголовков не будет
    router = Router()
    router.outer_middlewares.append(
        CORSMiddleware(allow_origins=["https://example.com"])
    )
    router.outer_middlewares.append(Raise())

    @router.get("/")
    async def handler() -> None: ...

    proto = call(App(router), headers={"origin": "https://example.com"})
    assert (proto.status, proto.payload) == (403, b'{"detail":"no"}')
    assert all(
        name != "access-control-allow-origin" for name, _ in proto.headers
    )


def test_outer_middleware_returned_error_gets_cors() -> None:
    router = Router()
    router.outer_middlewares.append(
        CORSMiddleware(allow_origins=["https://example.com"])
    )
    router.outer_middlewares.append(Deny())

    @router.get("/")
    async def handler() -> None: ...

    proto = call(App(router), headers={"origin": "https://example.com"})
    assert (proto.status, proto.payload) == (401, b'{"detail":"no"}')
    cors = ("access-control-allow-origin", "https://example.com")
    assert cors in proto.headers


def test_outer_middleware_unmapped_exception_is_500_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    router = Router()
    router.outer_middlewares.append(Crash())

    @router.get("/")
    async def handler() -> None: ...

    with caplog.at_level(logging.ERROR, logger="rapis"):
        proto = call(App(router))

    assert (proto.status, proto.payload) == (500, b"Internal Server Error")
    assert any(r.getMessage() == "unhandled error" for r in caplog.records)


def test_outer_cors_decorates_error_responses() -> None:
    router = Router()

    @router.get("/boom")
    async def boom() -> None:
        raise HTTPError(409, "conflict")

    router.outer_middlewares.append(
        CORSMiddleware(allow_origins=["https://example.com"])
    )
    app = App(router)
    origin = {"origin": "https://example.com"}
    cors = ("access-control-allow-origin", "https://example.com")

    boom_proto = call(app, path="/boom", headers=origin)
    assert boom_proto.status == 409
    assert cors in boom_proto.headers

    missing = call(app, path="/missing", headers=origin)
    assert missing.status == 404
    assert cors in missing.headers


class PassThrough:
    async def __call__(self, handler: Handler, request: Request) -> Response:
        return await handler(request)


@pytest.mark.parametrize("outer", [False, True], ids=["plain", "outer"])
def test_mapping_is_the_same_with_and_without_outer(outer: bool) -> None:
    router = Router()
    if outer:
        router.outer_middlewares.append(PassThrough())

    @router.get("/ok")
    async def ok() -> None: ...

    @router.get("/http")
    async def http() -> None:
        raise HTTPError(409, "conflict")

    @router.get("/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    app = App(router)
    assert call(app, path="/ok").status == 204
    assert call(app, path="/http").payload == b'{"detail":"conflict"}'
    assert call(app, path="/missing").payload == b'{"detail":"Not Found"}'
    assert call(app, path="/crash").status == 500
