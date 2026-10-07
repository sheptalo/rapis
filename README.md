# Rapis - Limitless Web-framework based on RSGI

[![Python versions](https://img.shields.io/pypi/pyversions/rapis.svg?color=%2334D058)](https://pypi.org/project/rapis)
[![Current version](https://img.shields.io/pypi/v/rapis?color=%2334D058&label=PyPI)](https://pypi.org/project/rapis)
[![Current status](https://img.shields.io/pypi/status/rapis)](https://pypi.org/project/rapis)
![PyPI - Downloads](https://img.shields.io/pypi/dm/rapis)

#### ⚠️ WARNING: Framework in pre-alpha state, a lot of changes incoming ⚠️

the main goal of this framework is to make expandable system for creating api with minimal dependencies and overhead

Key features:

- **Easy to use**: Syntax was inspired by your favourite framework
- **Fast**: contains only _1 dependency_ with minimal overhead see [benchmarks](benchmarks)
- **Async Only**: Supports only work with _async_ requests handling
- **Validation**: Built-in support of MsgSpec providing first-class Validation Speed
- **Minimalistic**: Framework contains _Minimal functional_ to build API

## Requirements

- [msgspec](https://github.com/jcrist/msgspec): A fast serialization and validation library

## Installation

```bash
pip install rapis
pip install granian # install any rsgi compatible web-server
# or simply
pip install rapis[standard] # includes granian in requirements
```

## Fast Start

```python
# main.py
from rapis import App, Router

router = Router()


@router.get("/")
async def root() -> dict:
    return {}


app = App(router)
```

### Run

```bash
granian main:app
```

## Moderate Example

```python
# routes.py
from msgspec import Struct
from rapis import MsgSpecParser, Router

router = Router()
# parameters without another source are read from the query string
router.parser = MsgSpecParser()


class Item(Struct):
    name: str


@router.get("/items/{item_id}")
async def get_item(item_id: int, verbose: bool = False) -> dict:
    # item_id comes from the path, verbose from the query string
    return {"id": item_id, "verbose": verbose}


@router.post("/items", status=201)
@MsgSpecParser("body")  # the JSON body is validated into Item
async def create_item(item: Item) -> Item:
    return item
```

```python
# main.py
from rapis import App

from routes import router

app = App(router)
```

### Where handler parameters come from

Resolved once, when the app is built, in this order:

1. annotated as `Request` — the request itself;
2. named like a `{placeholder}` of the path — converted to the annotated type;
3. listed in some middleware's `provides` — taken from `request.state`;
4. a parser: `MsgSpecParser("query")` (default) or `MsgSpecParser("body")`; a parser with `fields=[...]` takes exactly those names, a parser without `fields` takes the rest. Set it per handler as a decorator or per router with `router.parser = ...` (inherited by child routers);
5. otherwise the parameter needs a default value — a missing source raises `BuildError` at startup, not at request time.

Return values are encoded as JSON with the `status` of the route; `-> None` answers `204`, a returned `Response(status, headers, body)` is sent as is.

### Middlewares, errors

```python
from rapis import (
    App,
    CORSMiddleware,
    Handler,
    Header,
    HTTPError,
    Request,
    Response,
    Router,
)

root = Router()
# outer middlewares live on the root router only and wrap error responses too
root.outer_middlewares.append(CORSMiddleware(allow_origins=["https://example.com"]))


class Auth:
    provides = ("user",)  # the `user` parameter of handlers comes from request.state

    async def __call__(self, handler: Handler, request: Request) -> Response:
        request.state["user"] = request.scope.headers.get("x-user", "anonymous")
        return await handler(request)


api = Router(prefix="/api")
api.middlewares.append(Auth())  # this router and its children
root.include_router(api)


@api.get("/me")
async def me(user: str) -> dict:
    return {"user": user}


@api.route("/items/{item_id}", methods=["PUT", "PATCH"])  # methods without a shortcut
async def update_item(item_id: int) -> None:
    raise HTTPError(404, f"item {item_id} not found")  # 404 {"detail": "item 3 not found"}


app = App(root)
```

## Performance [benchmarks](benchmarks)

