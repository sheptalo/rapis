from rapis import AppRouter, WebApp

router = AppRouter()


@router.get("/")
async def root() -> dict:
    return {"Hello": "World!"}


app = WebApp()

app.include_router(router)
