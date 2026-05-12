from msgspec import Struct

from benchmarks.config import ROUTE_COUNT
from rapis import AppRouter, WebApp

router = AppRouter(prefix="/bench")


@router.get("/plain")
async def plain() -> dict:
    return {"ok": True}


class Payload(Struct):
    name: str
    count: int


@router.post("/validate")
async def validate(body: Payload) -> Payload:
    return body


for _i in range(ROUTE_COUNT):

    def _register(idx: int = _i):
        @router.get(f"/r/{idx}")
        async def route_many() -> dict:
            return {"i": idx}

        route_many.__name__ = f"bench_route_{idx}"

    _register()


app = WebApp(reraise_exception=False)
app.include_router(router)
