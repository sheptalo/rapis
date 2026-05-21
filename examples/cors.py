from rapis import AppRouter, WebApp
from rapis.abc.middleware import Middleware
from rapis.middlewares import CORSMiddleware

router = AppRouter()


@router.post("/")
async def root() -> dict:
    return {"Hello": "World!"}


app = WebApp(
    middlewares=[
        Middleware(CORSMiddleware, allow_origins=("http://127.0.0.1:8000",))
    ]  # try to send fetch from other origin
)

app.include_router(router)
