import functools
import inspect
import os
import re
from collections.abc import Awaitable, Callable, Generator, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, get_type_hints

import msgspec

from rapis.exceptions import BuildError
from rapis.responses import method_not_allowed, not_found
from rapis.router import Router
from rapis.serializer import json
from rapis.types import (
    PARAM,
    PARSER_LITERAL,
    SERIALIZER_LITERAL,
    Dynamic,
    Handler,
    HandlerSpec,
    Matcher,
    Middleware,
    Param,
    Parser,
    ParserCallable,
    Request,
    Response,
    Serializer,
    Step,
    Walked,
)

_GROUPS_FROM = 32


@dataclass(slots=True)
class _Route:
    call: Handler
    name: str


def _walk(
    router: "Router",
    prefix: str = "",
    inner: tuple[Middleware, ...] = (),
    parser: Parser | None = None,
    serializer: Serializer | None = None,
    *,
    root: bool = True,
) -> Generator[Walked, None, None]:
    if router.outer_middlewares and not root:
        raise BuildError("outer middlewares allowed only in root router")
    prefix += router.prefix
    inner += tuple(router.middlewares)
    parser = router.parser or parser
    serializer = router.serializer or serializer
    for spec in router.handlers:
        yield spec, prefix, inner, parser, serializer
    for child in router.children:
        yield from _walk(child, prefix, inner, parser, serializer, root=False)


def _compile(
    spec: HandlerSpec,
    prefix: str,
    inner: tuple[Middleware, ...],
    default_parser: Parser | None,
    default_serializer: Serializer | None,
) -> tuple[str, tuple[str, ...], _Route]:
    func = spec.func
    name = getattr(func, "__qualname__", repr(func))
    full_path = prefix + spec.path

    hints = get_type_hints(func)
    params = [
        Param(n, hints.get(n, str), p.default)
        for n, p in inspect.signature(func).parameters.items()
    ]
    found = PARAM.findall(full_path)
    path_names = set(found)
    if len(path_names) != len(found):
        raise BuildError(f"{name}: path params repeated {found}")
    provided = {key for mw in inner for key in getattr(mw, "provides", ())}

    parsers: list[Parser] = getattr(
        func, PARSER_LITERAL, [default_parser] if default_parser else []
    )
    rest = [pr for pr in parsers if pr.fields is None]
    if len(rest) > 1:
        raise BuildError(
            f"{name}: Only one parser can take the remaining parameters"
        )
    request_names, path_params, state_names, per_parser = _distribute(
        name, params, path_names, provided, parsers, rest
    )

    steps = [_put_request(n) for n in request_names]
    if path_params:
        steps.append(_put_path(path_params))
    if state_names:
        steps.append(_put_state(state_names))
    used = [pr for pr in parsers if per_parser[id(pr)]]
    steps += [_put_parsed(pr.build(per_parser[id(pr)])) for pr in used]

    serializer = getattr(func, SERIALIZER_LITERAL, default_serializer) or json
    render = serializer.build(
        hints.get("return", inspect.Parameter.empty), spec.status
    )
    call = _pipeline(
        func, _compose(steps), any(pr.needs_body for pr in used), render
    )
    for mw in reversed(inner):
        call = functools.partial(mw, call)
    return full_path, spec.methods, _Route(call, name)


def _distribute(
    name: str,
    params: Sequence[Param],
    path_names: set[str],
    provided: set[str],
    parsers: Sequence[Parser],
    rest: Sequence[Parser],
) -> tuple[list[str], list[Param], list[str], dict[int, list[Param]]]:
    explicit = {f: pr for pr in parsers if pr.fields for f in pr.fields}
    request_names, path_params, state_names = [], [], []
    per_parser: dict[int, list[Param]] = {id(pr): [] for pr in parsers}
    for p in params:
        if p.type is Request:
            request_names.append(p.name)
        elif p.name in path_names:
            path_params.append(p)
        elif p.name in provided:
            state_names.append(p.name)
        elif p.name in explicit:
            per_parser[id(explicit[p.name])].append(p)
        elif rest:
            per_parser[id(rest[0])].append(p)
        elif p.required:
            raise BuildError(
                f"{name}: parameter {p.name!r} seems to not have an source "
                "(path, middleware.provides, parser or default)"
            )
    if missing := path_names - {p.name for p in path_params}:
        raise BuildError(f"{name}: not allowed {sorted(missing)}")
    if unknown := set(explicit) - {p.name for p in params}:
        raise BuildError(f"{name}: unknown parser fields: {sorted(unknown)}")
    return request_names, path_params, state_names, per_parser


def _put_request(name: str) -> Step:
    def step(req: Request, kw: dict[str, Any]) -> None:
        kw[name] = req

    return step


def _put_path(params: Sequence[Param]) -> Step:
    names = [p.name for p in params]
    if all(p.type is str for p in params):

        def step_str(req: Request, kw: dict[str, Any]) -> None:
            for n in names:
                kw[n] = req.path_params[n]

        return step_str
    model = msgspec.defstruct(
        "PathParams", [(p.name, p.type) for p in params], kw_only=True
    )
    convert, asdict = msgspec.convert, msgspec.structs.asdict

    def slow(req: Request, kw: dict[str, Any]) -> None:
        kw.update(asdict(convert(req.path_params, model, strict=False)))

    if not all(p.type in (int, str) for p in params):
        return slow
    # int берём напрямую только из простой десятичной строки; всё остальное
    # (знак, пробелы, ведущие нули, не-ASCII) отдаём msgspec, чтобы ошибки
    # и результаты совпадали с прежними
    typed = [(p.name, p.type is int) for p in params]

    def step(req: Request, kw: dict[str, Any]) -> None:
        pp = req.path_params
        for n, is_int in typed:
            raw = pp[n]
            if is_int:
                if not (
                    raw.isdigit()
                    and raw.isascii()
                    and (raw == "0" or raw[0] != "0")
                ):
                    slow(req, kw)
                    return
                kw[n] = int(raw)
            else:
                kw[n] = raw

    return step


def _put_state(names: list[str]) -> Step:
    def step(req: Request, kw: dict[str, Any]) -> None:
        for n in names:
            kw[n] = req.state[n]

    return step


def _put_parsed(parse: ParserCallable) -> Step:
    def step(req: Request, kw: dict[str, Any]) -> None:
        kw.update(parse(req))

    return step


def _compose(steps: Sequence[Step]) -> ParserCallable | None:
    if not steps:
        return None
    if len(steps) == 1:
        (only,) = steps

        def bind_one(req: Request) -> dict[str, Any]:
            kw: dict[str, Any] = {}
            only(req, kw)
            return kw

        return bind_one
    steps = tuple(steps)

    def bind(req: Request) -> dict[str, Any]:
        kw: dict[str, Any] = {}
        for step in steps:
            step(req, kw)
        return kw

    return bind


def _pipeline(
    func: Callable[..., Awaitable[Any]],
    bind: ParserCallable | None,
    needs_body: bool,
    render: Callable[[Request], Response],
) -> Handler:

    if bind is None:

        async def run_plain(_req: Request) -> Response:
            result = await func()
            return render(result)

        return run_plain
    if needs_body:

        async def run_body(req: Request) -> Response:
            req.body = await req.proto()
            result = await func(**bind(req))
            return render(result)

        return run_body

    async def run(req: Request) -> Response:
        result = await func(**bind(req))
        return render(result)

    return run


def build_dispatch(router: "Router") -> Callable[[Request], Handler]:
    static: dict[str, dict[str, Any]] = {}
    dynamic: dict[str, dict[str, Any]] = {}
    for spec, prefix, inner, parser, serializer in _walk(router):
        full_path, methods, route = _compile(
            spec, prefix, inner, parser, serializer
        )
        table = (dynamic if PARAM.search(full_path) else static).setdefault(
            full_path, {}
        )
        for m in methods:
            table.setdefault(m, []).append(route)

    for table in [*static.values(), *dynamic.values()]:
        for method, routes in table.items():
            plain = [r.name for r in routes]
            if len(plain) > 1:
                raise BuildError(f"ambiguous handlers for {method}: {plain}")
            table[method] = routes[0].call

    return _dispatcher(static, dynamic)


def _alternation(routes: Iterable[tuple[str, dict[str, Any]]]) -> Matcher:
    alternatives: list[str] = []
    by_last: dict[int | None, Dynamic] = {}
    group = 0
    for full_path, table in routes:
        parts = PARAM.split(full_path)
        groups = []
        for name in parts[1::2]:
            group += 1
            groups.append((name, group))
        alternatives.append(
            "".join(
                "([^/]+)" if i % 2 else re.escape(part)
                for i, part in enumerate(parts)
            )
        )
        by_last[group] = (table, groups)
    return re.compile("|".join(alternatives) or "(?!)").fullmatch, by_last


def _dispatcher(
    static: dict[str, dict[str, Any]], dynamic: dict[str, dict[str, Any]]
) -> Callable[[Request], Handler]:
    groups: dict[str, Matcher] = {}
    ungrouped = _alternation(dynamic.items())
    start = 0
    if len(dynamic) >= _GROUPS_FROM:
        common = os.path.commonprefix(list(dynamic)).partition("{")[0]
        start = common.rfind("/") + 1
        keyed = [
            (full_path[start:].partition("/")[0], (full_path, table))
            for full_path, table in dynamic.items()
        ]
        groups = {
            key: _alternation(r for k, r in keyed if k == key or "{" in k)
            for key in {k for k, _ in keyed if "{" not in k}
        }
        ungrouped = _alternation(r for k, r in keyed if "{" in k)

    def resolve(req: Request) -> Handler:
        scope = req.scope
        path = scope.path
        table = static.get(path)
        if table is None:
            match, by_last = (
                groups.get(path[start : path.find("/", start)], ungrouped)
                if groups
                else ungrouped
            )
            found = match(path)
            if found is None:
                return not_found
            table, params = by_last[found.lastindex]
            req.path_params = {name: found.group(i) for name, i in params}
        handler: Handler | None = table.get(scope.method) or table.get("*")
        if handler is None:
            allow = ", ".join(sorted(table))
            return functools.partial(method_not_allowed, allow)
        return handler

    return resolve
