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
- **OpenAPI**: Documentate your API (QoL changes WIP)

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
from rapis import AppRouter, WebApp

router = AppRouter()


@router.get("/")
async def root() -> dict:
    return {}


app = WebApp()
app.include_router(router)

```

### Run

```bash
granian main:app
```

## Moderate Example

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

### More [examples](examples)

## Performance [benchmarks](benchmarks)

## [Wiki](https://github.com/sheptalo/rapis/wiki)

## TODO

- [ ] MAKE FRAMEWORK EASY TO EXTEND, EASY TO OVERRIDE (DIP, and other things included)
- [ ] coverage (atleast 80%)
- [ ] Test Client
- [ ] Docs
- [ ] life cycle
- [ ] Problem: how to authenticate users?
- [ ] Problem: how to send files? (receive files: like query, send files: ??)
- [ ] Problem: how to work with cookies? (get cookies: like query, send cookies: ??)
- [ ] https://jcristharif.com/msgspec/perf-tips.html (reduce latency more)
- [X] Exception handling
- [X] Built-in exception handlers (validation, json parsing)
- [X] Benchmarks section
- [X] better Query params handle
- [X] change routing from linear to something else (hash maps for static paths, ?? for dynamic paths)
- [X] path patterns logic
- [X] review Middleware logic
- [X] typing support in TY
- [X] some examples
