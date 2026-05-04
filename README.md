# Rapis - Minimalistic web library based on RSGI

_this library was inspired by FastAPI so syntax may be identical_

### ! WARNING: Library in early development, it is NOT READY for production

Key features:

- **Easy to use**: Syntax was inspired by your favourite framework
- **Fast**: Built on Granian in native RSGI protocol with MsgSpec support
- **Async Only**: Supports only work with async requests handling

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
