#!/usr/bin/env python3
"""Lightweight API compatibility guard.

Checks a minimal set of OpenAPI contracts for critical public endpoints.
Intended to fail fast when key paths or response contracts drift unexpectedly.
"""

from __future__ import annotations

from typing import Any

from grantflow.api.app import app

REQUIRED_SECURITY_SCHEME = "ApiKeyAuth"

# path -> required methods
REQUIRED_PATHS: dict[str, set[str]] = {
    "/health": {"get"},
    "/generate": {"post"},
    "/generate/from-preset": {"post"},
    "/status/{job_id}": {"get"},
    "/status/{job_id}/quality": {"get"},
    "/status/{job_id}/critic": {"get"},
    "/status/{job_id}/review/workflow": {"get"},
    "/export": {"post"},
}

# path/method tuples that must document a 200 JSON response schema
REQUIRED_200_JSON_SCHEMA: set[tuple[str, str]] = {
    ("/health", "get"),
    ("/generate", "post"),
    ("/generate/from-preset", "post"),
    ("/status/{job_id}", "get"),
    ("/status/{job_id}/quality", "get"),
    ("/status/{job_id}/critic", "get"),
    ("/status/{job_id}/review/workflow", "get"),
}


def _fail(msg: str) -> None:
    raise SystemExit(msg)


def _get_json_schema_for_200(op: dict[str, Any]) -> dict[str, Any] | None:
    responses = op.get("responses") if isinstance(op, dict) else None
    if not isinstance(responses, dict):
        return None
    ok = responses.get("200")
    if not isinstance(ok, dict):
        return None
    content = ok.get("content")
    if not isinstance(content, dict):
        return None
    app_json = content.get("application/json")
    if not isinstance(app_json, dict):
        return None
    schema = app_json.get("schema")
    return schema if isinstance(schema, dict) else None


def main() -> int:
    spec = app.openapi()

    components = spec.get("components") if isinstance(spec, dict) else None
    security_schemes = (components or {}).get("securitySchemes") if isinstance(components, dict) else None
    if not isinstance(security_schemes, dict) or REQUIRED_SECURITY_SCHEME not in security_schemes:
        _fail(f"Missing required security scheme: {REQUIRED_SECURITY_SCHEME}")

    paths = spec.get("paths") if isinstance(spec, dict) else None
    if not isinstance(paths, dict):
        _fail("OpenAPI spec missing paths")

    for path, methods in REQUIRED_PATHS.items():
        path_item = paths.get(path)
        if not isinstance(path_item, dict):
            _fail(f"Missing required path: {path}")
        for method in methods:
            op = path_item.get(method)
            if not isinstance(op, dict):
                _fail(f"Missing required operation: {method.upper()} {path}")

    for path, method in sorted(REQUIRED_200_JSON_SCHEMA):
        op = ((paths.get(path) or {}) if isinstance(paths.get(path), dict) else {}).get(method)
        if not isinstance(op, dict):
            _fail(f"Missing operation while checking schema: {method.upper()} {path}")
        schema = _get_json_schema_for_200(op)
        if not schema:
            _fail(f"Missing 200 application/json schema for: {method.upper()} {path}")

    print("API contract guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
