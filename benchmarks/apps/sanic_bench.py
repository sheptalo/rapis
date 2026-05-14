from sanic import Sanic
from sanic.response import json
from sanic import Request
from msgspec import Struct

from benchmarks.config import ROUTE_COUNT


class Payload(Struct):
    name: str
    count: int


app = Sanic("bench")


@app.route("/bench/plain", methods=["GET"])
async def plain(request: Request):
    return json({"ok": True})


@app.route("/bench/validate", methods=["POST"])
async def validate(request: Request):
    data = request.json
    payload = Payload(**data)
    return json({"name": payload.name, "count": payload.count})


@app.route("/bench/large", methods=["GET"])
async def large(request: Request):
    return json({"data": list(range(1000))})


@app.route("/bench/query", methods=["GET"])
async def query(request: Request):
    skip = request.args.get("skip", "0")
    limit = request.args.get("limit", "10")
    return json({"skip": int(skip), "limit": int(limit)})


for _i in range(ROUTE_COUNT):

    @app.route(f"/bench/r/{_i}", methods=["GET"], name=f"route_{_i}")
    async def route_many(request: Request, idx=_i):
        return json({"i": idx})


@app.route("/bench/d/{idx}", methods=["GET"])
async def route_dynamic(request: Request, idx: int):
    return json({"i": idx})
