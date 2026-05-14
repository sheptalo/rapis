from benchmarks.config import ROUTE_COUNT, TARGET_ROUTE_INDEX
from fastapi import APIRouter, FastAPI, Query
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


@bench.get("/large")
async def large() -> dict:
    return {"data": list(range(1000))}


@bench.get("/query")
async def query(skip: int = Query(0), limit: int = Query(10)) -> dict:
    return {"skip": skip, "limit": limit}


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

@bench.get("/d/{idx}")
async def route_dynamic(idx: int) -> dict:
    return {"i": idx}


app = FastAPI()
app.include_router(bench)
