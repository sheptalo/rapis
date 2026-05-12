from litestar import Litestar
from litestar.handlers.http_handlers import get, post
from pydantic import BaseModel

from benchmarks.config import ROUTE_COUNT


class Payload(BaseModel):
    name: str
    count: int


@get("/bench/plain")
async def plain() -> dict:
    return {"ok": True}


@post("/bench/validate")
async def validate(data: Payload) -> Payload:
    return data


handlers: list = [plain, validate]

for _i in range(ROUTE_COUNT):

    async def route_many(idx: int = _i) -> dict:
        return {"i": idx}

    route_many.__name__ = f"bench_route_{_i}"
    handlers.append(get(f"/bench/r/{_i}")(route_many))

app = Litestar(handlers)
