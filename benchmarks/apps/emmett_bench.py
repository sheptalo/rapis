import json

from emmett import App, Field, Form, request, response

from benchmarks.config import ROUTE_COUNT

app = App(__name__)

JSON_HEADERS = {"content-type": "application/json"}
OK_RESPONSE = b'{"ok":true}'

schema = {
    'name': Field(),
    'count': Field("int")
}

@app.route("/bench/plain", methods="get", pipeline=[])
async def plain():
    response.headers.update(JSON_HEADERS)
    return OK_RESPONSE

@app.route("/bench/validate", methods="post", pipeline=[])
async def validate():
    form = Form(schema)
    if form.accepted:
        return form.fields
    return {}

@app.route("/bench/large", methods="get", pipeline=[])
async def large():
    response.headers.update(JSON_HEADERS)
    return {"data": list(range(1000))}

@app.route("/bench/query", methods="get", pipeline=[])
async def query():
    response.headers.update(JSON_HEADERS)
    qp = request.query_params
    body = {
        "skip": int(qp.get("skip", "0")),
        "limit": int(qp.get("limit", "10")),
    }
    return json.dumps(body, separators=(",", ":")).encode("ascii")

for _i in range(ROUTE_COUNT):
    @app.route(f"/bench/r/{_i}", methods="get", name=f"r_{_i}", pipeline=[])
    async def route_many(idx=_i):
        return f'{{"i":{idx}}}'


@app.route("/bench/d/{idx}", methods="get", pipeline=[])
async def route_dynamic(idx: int):
    return f'{{"i":{idx}}}'
