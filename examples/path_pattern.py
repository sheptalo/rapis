from uuid import UUID

from rapis import AppRouter, WebApp

router = AppRouter()


@router.get("/{value}")
async def root(value: UUID) -> UUID:
    return value


app = WebApp()

app.include_router(router)
