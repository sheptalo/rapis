from collections.abc import Mapping

import msgspec

from rapis.types import HttpProtocol, Scope


class Request:
    def __init__(self, scope: Scope, proto: HttpProtocol) -> None:
        self._scope = scope
        self._proto = proto
        self._body = None

    @property
    async def body(self) -> dict:
        if self._body is None:
            self._body = msgspec.json.decode(await self._proto())
        return self._body

    @property
    async def method(self) -> str:
        return self._scope.method

    @property
    async def headers(self) -> Mapping[str, str]:
        return self._scope.headers

    @property
    async def path(self) -> str:
        return self._scope.path

    @property
    async def query_string(self) -> str:
        return self._scope.query_string

    @property
    async def authority(self) -> str | None:
        return self._scope.authority
