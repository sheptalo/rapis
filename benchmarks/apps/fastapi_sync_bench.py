from benchmarks.config import ROUTE_COUNT
from fastapi import APIRouter, FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

class Payload(BaseModel):
    name: str
    count: int

bench = APIRouter(prefix="/bench")

@bench.get("/plain")
def plain():
    return {"ok": True}

@bench.post("/validate")
def validate(p: Payload):
    return p

@bench.get("/large")
def large():
    return {"data": list(range(1000))}

@bench.get("/query")
def query(skip: int = Query(0), limit: int = Query(10)):
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
def route_dynamic(idx: int) -> dict:
    return {"i": idx}


app.include_router(bench)
