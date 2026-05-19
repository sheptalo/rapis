# Rapis - Minimalistic web framework based on RSGI

[![Python versions](https://img.shields.io/pypi/pyversions/rapis.svg?color=%2334D058)](https://pypi.org/project/rapis)
[![Current version](https://img.shields.io/pypi/v/rapis?color=%2334D058&label=PyPI)](https://pypi.org/project/rapis)
[![Current status](https://img.shields.io/pypi/status/rapis)](https://pypi.org/project/rapis)
![PyPI - Downloads](https://img.shields.io/pypi/dm/rapis)

_this framework was inspired by FastAPI so syntax may be identical_

### ⚠️ WARNING: Framework in early development, it is NOT READY for production

Key features:

- **Easy to use**: Syntax was inspired by your favourite framework
- **Fast**: Built on native RSGI protocol with MsgSpec support
- **Async Only**: Supports only work with async requests handling
- **Validation**: Built-in support of MsgSpec providing first-class Validation Speed
- **Functional that actually MATTER**: Framework contains _Only_ what you need to build API _without unnecessary_ dependencies
- **OpenAPI**: Documentate your API

## Requirements

- [msgspec](https://github.com/jcrist/msgspec): A fast serialization and validation library

## Installation

```bash
pip install rapis
# install any rsgi compatible web-server
pip install granian
# or simply
pip install rapis[standard] # includes granian in requirements
```

## Example

```python
# main.py
from rapis import AppRouter, Query, WebApp

router = AppRouter()


@router.get("/")
async def root() -> dict:
    return {}


@router.get("/echo")
async def parametrized_handler(
    data: Query[str] = "default",
) -> str:  # for now waiting for /echo?data=str if not given adds "default"
    return data


app = WebApp()
app.include_router(router)

```

### Run

```bash
granian main:app
```

## Better Example

```python
# routes.py
from msgspec import Struct
from rapis import AppRouter, Query

router = AppRouter()


class Item(Struct):
    name: str


@router.get("/queries_with_struct")
async def fetch_item(item: Query[Item]):  # no default means required and will expect to receive all fields in query params
    return Item(name="query")  # automatically parses to {"name": "query"}


@router.post("/echo") # also put, patch
async def fetch_item(item: Item):  # will try to read and validate all fields from body
    return item

```

```python
# main.py
from rapis import WebApp

from routes import router

app = WebApp()
app.include_router(router)
```

more [examples](examples)

## Performance

see [benchmarks](benchmarks)

## Docs

see [wiki](https://github.com/sheptalo/rapis/wiki)

## TODO

- [X] Exception handling
- [X] Built-in exception handlers (validation, json parsing)
- [X] Benchmarks section
- [ ] Request/Response Work model
- [ ] Docs
- [ ] More availabilities to expand logic (custom routes and other)
- [X] better Query params handle
- [X] change routing from linear to something else (hash maps for static paths, ?? for dynamic paths)
- [X] path patterns logic
- [X] review Middleware logic
- [ ] websocket support(maybe)
- [ ] coverage
- [X] typing support in TY
- [X] some examples
- [ ] Problem: how to authenticate users?
- [ ] Problem: how to send files?
- [ ] Problem: how to work with cookies?
- [ ] https://jcristharif.com/msgspec/perf-tips.html

## CONTRIBUTING

see [CONTRIBUTING.md](CONTRIBUTING.md)
