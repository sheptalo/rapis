from collections.abc import Callable, Collection, Sequence
from http import HTTPMethod, HTTPStatus

from rapis.entities.handler import Handler
from rapis.entities.middleware import Middleware
from rapis.entities.route import Route
from rapis.routing._handle import route
from rapis.services.bindings import (
    extract_bindings,
    extract_path_param_types,
)
from rapis.services.path_pattern import (
    compile_path_pattern,
    normalize_route_path,
)
from rapis.types import HttpProtocol, Scope


class APIRoute(Route):
    def __init__(
        self,
        path: str,
        endpoint: Callable | Handler,
        status: HTTPStatus,
        *,
        methods: Collection[HTTPMethod] | None = None,
        middleware: Sequence[Middleware] | None = None,
        description: str | None = "",
        summary: str | None = "",
        tags: Sequence[str] | None = None,
    ) -> None:
        self._route_path = normalize_route_path(path)
        self.status = status
        if isinstance(endpoint, Handler):
            self._handler = endpoint
            self._refresh_handler_path_matching()
            self.app = route(endpoint)
        else:
            path_pat, fields = compile_path_pattern(self._route_path)
            path_types = extract_path_param_types(endpoint, fields)
            bindings = [
                b for b in extract_bindings(endpoint) if b.name not in fields
            ]
            self._handler = Handler(
                call=endpoint,
                bindings=bindings,
                status=status,
                path_pattern=path_pat,
                path_fields=fields,
                path_types=path_types,
            )
            self.app = route(self._handler)

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)
        self.tags = tags or []
        self.description = description
        self.summary = summary
        self.methods = methods or [HTTPMethod.GET]

    async def __call__(self, scope: Scope, proto: HttpProtocol) -> None:
        if self.methods and scope.method not in self.methods:
            headers = [("Allow", ", ".join(sorted(self.methods)))]
            proto.response_str(
                HTTPStatus.METHOD_NOT_ALLOWED, headers, "Method Not Allowed"
            )
            return

        await self.app(scope, proto)

    @property
    def path(self) -> str:
        return self._route_path

    @path.setter
    def path(self, value: str) -> None:
        self._route_path = normalize_route_path(value)
        self._refresh_handler_path_matching()

    def _refresh_handler_path_matching(self) -> None:
        path_pat, fields = compile_path_pattern(self._route_path)
        types_m = extract_path_param_types(self._handler.call, fields)
        self._handler.set_path_matching(
            pattern=path_pat, fields=fields, types=types_m
        )

    def matches(self, scope: Scope) -> bool:
        if self._handler.path_pattern is None:
            return scope.path == self._route_path
        return self._handler.path_pattern.fullmatch(scope.path) is not None

    @property
    def handler(self) -> Handler:
        return self._handler

    def static(self) -> bool:
        return self._handler.path_pattern is None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(path={self.path!r}, "
            f"methods={sorted(self.methods or [])!r})"
        )
