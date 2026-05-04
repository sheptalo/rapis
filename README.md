# Rapis - Minimalistic web library

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

## Installation

### ! WARNING: Library in early development, it is NOT READY for production

### from Pypi

#### WIP

### from source

```bash
git clone https://github.com/sheptalo/rapis folder
pip install ./folder
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