from rapis import AppRouter

app = AppRouter()  # router is also an App in some ways


@app.get("/")
async def root() -> dict:
    return {"Hello": "World!"}
