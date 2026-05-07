from collections.abc import Callable
from http import HTTPStatus


class Handler:
    def __init__(
        self, call: Callable, bindings: list, status: HTTPStatus
    ) -> None:
        self.call = call
        self.status = status
        self.path_fields: frozenset[str] = frozenset()
        self.bindings = bindings
