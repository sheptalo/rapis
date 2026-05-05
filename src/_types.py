from collections.abc import Awaitable, Callable

from granian._granian import RSGIHTTPProtocol
from granian.rsgi import Scope

type RSGIApp = Callable[[Scope, RSGIHTTPProtocol], Awaitable[None]]


type Query[T] = T
