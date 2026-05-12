from emmett import App, Form, response, Field
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

for _i in range(ROUTE_COUNT):
    @app.route(f"/bench/r/{_i}", methods="get", name=f"r_{_i}", pipeline=[])
    async def route_many(idx=_i):
        return f'{{"i":{idx}}}'
