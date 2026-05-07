import msgspec

from rapis.entities.handler import Handler
from rapis.exceptions import ValidationError
from rapis.services.bindings import parse_bindings
from rapis.types import HttpProtocol, RSGIApp, Scope


def route(handler: Handler) -> RSGIApp:
    async def wrapper(scope: Scope, proto: HttpProtocol) -> None:
        parsed_kwargs, parsed_errors = await parse_bindings(
            handler, scope, proto
        )
        if parsed_errors:
            raise ValidationError(errors=parsed_errors)
        result = await handler.call(**parsed_kwargs)
        if isinstance(result, msgspec.Struct | dict):
            payload = msgspec.json.encode(result)
        elif isinstance(result, str):
            payload = result.encode()
        else:
            payload = str(result).encode()

        proto.response_bytes(
            handler.status, [("Content-Type", "application/json")], payload
        )

    return wrapper
