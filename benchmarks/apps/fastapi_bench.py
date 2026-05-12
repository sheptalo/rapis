from benchmarks.config import ROUTE_COUNT
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel


class Payload(BaseModel):
    name: str
    count: int


bench = APIRouter(prefix="/bench")


@bench.get("/plain")
async def plain() -> dict:
    return {"ok": True}


@bench.post("/validate")
async def validate(p: Payload) -> Payload:
    return p

def create_route_handler(idx: int):
    def route_many():
        return {"i": idx}
    return route_many

for _i in range(ROUTE_COUNT):
    handler = create_route_handler(_i)
    bench.add_api_route(
        f"/r/{_i}",
        handler,
        methods=["GET"],
        name=f"bench_route_{_i}"
    )

app = FastAPI()
app.include_router(bench)
