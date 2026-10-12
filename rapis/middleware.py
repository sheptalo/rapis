from collections.abc import Sequence

from rapis.types import Handler, Request, Response


class CORSMiddleware:
    def __init__(
        self,
        allow_origins: Sequence[str] = ("*",),
        allow_methods: Sequence[str] = (
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ),
        max_age: int = 600,
    ) -> None:
        self.origins = frozenset(allow_origins)
        self.any_origin = "*" in self.origins
        self.preflight = [
            ("access-control-allow-methods", ", ".join(allow_methods)),
            ("access-control-max-age", str(max_age)),
        ]

    async def __call__(self, handler: Handler, request: Request) -> Response:
        headers = request.scope.headers
        origin = headers.get("origin")
        if origin is None or not (self.any_origin or origin in self.origins):
            return await handler(request)
        cors = [
            (
                "access-control-allow-origin",
                "*" if self.any_origin else origin,
            ),
            ("vary", "origin"),
        ]
        if request.scope.method == "OPTIONS" and headers.get(
            "access-control-request-method"
        ):
            requested = headers.get("access-control-request-headers")
            extra = (
                [("access-control-allow-headers", requested)]
                if requested
                else []
            )
            return Response(204, cors + self.preflight + extra)
        response = await handler(request)
        response.headers = response.headers + cors
        return response
