# Rapis - Minimalistic web library based on RSGI

this library was inspired by FastAPI so syntax may be identical

```python
from rapis import AppRouter, WebApp

app = WebApp()
router = AppRouter()


@router.get("/")
async def root() -> dict:
    return {}


app.include_router(router)
```

## BENCHMARKS

section about speed of library (WIP)

## Installation

### ! WARNING: Library in early development, it is NOT READY for production

### from Pypi

```bash
pip install rapis
```

## DOCS will be implemented soon

## TODO

- [ ] Exception handling
- [ ] Request/Response Work model
- [ ] Docs
- [ ] More availabilities to expand logic
- [ ] better Query params handle
- [ ] chage routing from linear to something else
- [ ] rewrite path patterns logic
- [ ] review Middleware logic (it was taked from fastapi)
- [ ] websocket support(maybe)
- [ ] coverage
- [ ] typing support (for now a few Errors in mypy, maybe start using TY)

## CONTRIBUTING

see [CONTRIBUTING.md](CONTRIBUTING.md)
