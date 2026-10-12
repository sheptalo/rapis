import inspect
from typing import Any

from rapis.responses import json_response
from rapis.types import Response, Serializer, SerializerCallable


class JsonSerializer(Serializer):
    def build(self, tp: Any, status: int) -> SerializerCallable:
        if tp is None or tp is type(None):
            code = 204 if status == 200 else status
            return lambda _value: Response(code)
        if isinstance(tp, type) and issubclass(tp, Response):
            return lambda value: value
        if tp is Any or tp is inspect.Parameter.empty:
            return lambda value: (
                value
                if isinstance(value, Response)
                else json_response(value, status)
            )
        return lambda value: json_response(value, status)


json = JsonSerializer()
