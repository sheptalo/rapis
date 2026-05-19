import inspect
import json
from collections.abc import Iterator
from http import HTTPMethod, HTTPStatus
from typing import Any, get_args, get_origin, get_type_hints

import msgspec

from rapis.entities.bindings import ParamBindingSource
from rapis.entities.handler import Handler
from rapis.entities.response import Response
from rapis.entities.route import Route
from rapis.openapi.config import OpenAPIConfig
from rapis.routing import AppRouter
from rapis.services.path_pattern import normalize_route_path
from rapis.types import Query


def _iter_routes(router: AppRouter) -> Iterator[Route]:
    yield from router.static_routes.values()
    yield from router.dynamic_routes


def _schema_for_type(typ: Any, components: dict[str, Any]) -> dict[str, Any]:
    raw = msgspec.json.schema(typ, ref_template="#/components/schemas/{name}")
    components.update(raw.pop("$defs", {}))
    return raw


def _binding_required(sig: inspect.Signature, name: str) -> bool:
    param = sig.parameters[name]
    return param.default is inspect.Parameter.empty


def _method_reads_body(method: str) -> bool:
    return method in {"POST", "PUT", "PATCH"}


def _operation_parameters(
    handler: Handler,
    sig: inspect.Signature,
    components: dict[str, Any],
) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    for name, typ in handler.path_types.items():
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": _schema_for_type(typ, components),
            },
        )

    for b in handler.bindings:
        if b.source != ParamBindingSource.query:
            continue
        inner = b.type
        origin = get_origin(inner)
        if origin is Query:
            inner_args = get_args(inner)
            inner = inner_args[0] if inner_args else str

        param_def: dict[str, Any] = {
            "name": b.name,
            "in": "query",
            "required": _binding_required(sig, b.name),
            "schema": _schema_for_type(inner, components),
        }
        params.append(param_def)

    return params


def _operation_request_body(
    handler: Handler,
    sig: inspect.Signature,
    components: dict[str, Any],
) -> dict[str, Any] | None:
    body_bindings = [
        b for b in handler.bindings if b.source == ParamBindingSource.body
    ]
    if not body_bindings:
        return None

    required_any = any(_binding_required(sig, b.name) for b in body_bindings)

    if len(body_bindings) == 1 and body_bindings[0].is_struct:
        schema = _schema_for_type(body_bindings[0].type, components)
    else:
        props = {}
        req_names: list[str] = []
        for b in body_bindings:
            props[b.name] = _schema_for_type(b.type, components)
            if _binding_required(sig, b.name):
                req_names.append(b.name)
        schema_body: dict[str, Any] = {
            "type": "object",
            "properties": props,
        }
        if req_names:
            schema_body["required"] = req_names
        schema = schema_body

    return {
        "required": required_any,
        "content": {"application/json": {"schema": schema}},
    }


def _operation_responses(
    route: Route, components: dict[str, Any]
) -> dict[Any, Any]:
    hints = get_type_hints(route.handler.call, include_extras=True)
    ret = hints.get("return")
    if ret is None or ret is inspect.Signature.empty:
        schema: dict[str, Any] = {"type": "object"}
    else:
        schema = _schema_for_type(ret, components)

    return {
        route.status: {
            "description": route.status,
            "content": {"application/json": {"schema": schema}},
        },
    }


def _build_operation(
    route: Route,
    method: str,
    components: dict[str, Any],
) -> dict[str, Any]:
    handler = route.handler
    sig = inspect.signature(handler.call)
    op: dict[str, Any] = {
        "operationId": (
            f"{getattr(handler.call, '__name__', 'handler')}_{method.lower()}"
        ),
        "summary": route.summary,
        "description": route.description,
        "tags": route.tags,
        "responses": _operation_responses(route, components),
        "parameters": _operation_parameters(handler, sig, components),
    }
    if _method_reads_body(method):
        body = _operation_request_body(handler, sig, components)
        if body is not None:
            op["requestBody"] = body
    return op


def build_openapi_spec(
    router: AppRouter, config: OpenAPIConfig
) -> dict[str, Any]:
    components: dict[str, Any] = {}
    paths: dict[str, dict[str, Any]] = {}

    for route in _iter_routes(router):
        path_key = route.path or "/"
        path_item = paths.setdefault(path_key, {})
        methods = sorted(m for m in route.methods if m != HTTPMethod.OPTIONS)
        for method in methods:
            path_item[method.lower()] = _build_operation(
                route,
                method,
                components,
            )

    spec: dict[str, Any] = {
        "openapi": config.openapi_version,
        "info": {
            "title": config.title,
            "version": config.version,
        },
        "paths": paths,
    }
    spec["info"]["description"] = config.description or ""
    spec["components"] = {"schemas": components}
    return spec


def swagger_ui_page(openapi_url: str, page_title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <link rel="stylesheet"
    href="https://unpkg.com/swagger-ui-dist@5.32.6/swagger-ui.css"
    crossorigin="anonymous" />
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.32.6/swagger-ui-bundle.js"
  crossorigin="anonymous"></script>
<script>
  window.onload = () => {{
    SwaggerUIBundle({{
      url: {json.dumps(openapi_url)},
      dom_id: '#swagger-ui',
    }});
  }};
</script>
</body>
</html>"""


def attach_openapi_routes(
    *,
    router: AppRouter,
    schema_bytes: bytes,
    config: OpenAPIConfig,
) -> None:
    prefix = router.prefix
    json_path = normalize_route_path(prefix + config.openapi_path)
    docs_path = normalize_route_path(prefix + config.docs_path)

    async def serve_openapi_schema() -> Response:
        return Response(
            schema_bytes,
            HTTPStatus.OK,
            [("Content-Type", "application/json; charset=utf-8")],
        )

    page = swagger_ui_page(openapi_url=json_path, page_title=config.title)

    async def serve_swagger_ui() -> Response:
        return Response(
            page,
            HTTPStatus.OK,
            [("Content-Type", "text/html; charset=utf-8")],
        )

    router.static_routes[json_path] = router.route_class(
        path=json_path,
        endpoint=serve_openapi_schema,
        status=HTTPStatus.OK,
        methods=[HTTPMethod.GET],
        middleware=[],
    )
    router.static_routes[docs_path] = router.route_class(
        path=docs_path,
        endpoint=serve_swagger_ui,
        status=HTTPStatus.OK,
        methods=[HTTPMethod.GET],
        middleware=[],
    )
