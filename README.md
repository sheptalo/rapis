# Rapis - Minimalistic web library based on RSGI

_this library was inspired by FastAPI so syntax may be identical_

### ! WARNING: Library in early development, it is NOT READY for production

Key features:

- **Easy to use**: Syntax was inspired by your favourite framework
- **Fast**: Built on Granian in native RSGI protocol with MsgSpec support
- **Async Only**: Supports only work with async requests handling
- **Validation**: Built-in support of MsgSpec providing first-class Validation Speed
- **Functional that actually MATTER**: Framework contains _Only_ what you need to build API _without unnecessary_ dependencies

## Requirements

- [granian](https://github.com/emmett-framework/granian): A Rust HTTP server for Python applications
- [msgspec](https://github.com/jcrist/msgspec): A fast serialization and validation library


## Installation


```bash
pip install rapis
```

## Example

```python
# main.py
from rapis import AppRouter, WebApp

app = WebApp()
router = AppRouter()


@router.get("/")
async def root() -> dict:
    return {}


app.include_router(router)
```

### Run

```bash
granian main:app
```

## Performance

section about speed of library (WIP)

## DOCS will be implemented soon

## TODO

- [ ] Exception handling
- [ ] path params
- [ ] Benchmarks section
- [ ] Request/Response Work model
- [ ] Docs
- [ ] More availabilities to expand logic (custom routes and other)
- [ ] better Query params handle (for now not fully tested)
- [ ] chage routing from linear to something else (hash maps for static paths, ?? for dynamic paths)
- [ ] rewrite path patterns logic (without context vars)
- [ ] review Middleware logic (it was taked from fastapi)
- [ ] websocket support(maybe)
- [ ] coverage
- [X] typing support in TY

## CONTRIBUTING

see [CONTRIBUTING.md](CONTRIBUTING.md)
