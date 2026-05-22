from functools import wraps
from http import HTTPStatus

import msgspec

from rapis.abc.endpoint import Endpoint
from rapis.entities.response import Response
from rapis.exceptions import ValidationError
from rapis.services.bindings import parse_bindings
from rapis.services.path_pattern import path_captures
from rapis.types import HttpProtocol, RSGIApp, Scope


def route(handler: Endpoint, status: HTTPStatus) -> RSGIApp:
    @wraps(handler.call)
    async def wrapper(scope: Scope, proto: HttpProtocol) -> None:
        raw_paths = path_captures(handler.path_pattern, scope.path)
        kwargs, errs = await parse_bindings(handler, scope, proto, raw_paths)
        if errs:
            raise ValidationError(errors=errs)
        result = await handler.call(**kwargs)
        if isinstance(result, Response):
            result(scope, proto)
            return
        if isinstance(result, msgspec.Struct | dict):
            payload = msgspec.json.encode(result)
        elif isinstance(result, str):
            payload = result.encode()
        else:
            payload = str(result).encode()

        proto.response_bytes(
            status, [("Content-Type", "application/json")], payload
        )

    return wrapper
