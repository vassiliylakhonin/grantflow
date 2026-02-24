from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi


PROTECTED_OPERATIONS = {
    ("post", "/generate"),
    ("post", "/ingest"),
    ("post", "/cancel/{job_id}"),
    ("post", "/resume/{job_id}"),
    ("post", "/hitl/approve"),
    ("post", "/export"),
    ("get", "/status/{job_id}"),
    ("get", "/status/{job_id}/citations"),
    ("get", "/status/{job_id}/versions"),
    ("get", "/status/{job_id}/diff"),
    ("get", "/status/{job_id}/events"),
    ("get", "/hitl/pending"),
}


def api_key_configured() -> str | None:
    return os.getenv("GRANTFLOW_API_KEY") or os.getenv("API_KEY")


def read_auth_required() -> bool:
    return os.getenv("GRANTFLOW_REQUIRE_AUTH_FOR_READS", "false").strip().lower() == "true"


def require_api_key_if_configured(request: Request, *, for_read: bool = False) -> None:
    expected = api_key_configured()
    if not expected:
        return
    if for_read and not read_auth_required():
        return

    provided = request.headers.get("x-api-key")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def install_openapi_api_key_security(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=(
                f"{app.description}\n\n"
                "Optional API key auth: set `GRANTFLOW_API_KEY` on the server and send "
                "`X-API-Key` on protected endpoints. Reads can also require auth when "
                "`GRANTFLOW_REQUIRE_AUTH_FOR_READS=true`."
            ),
            routes=app.routes,
        )

        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["ApiKeyAuth"] = {"type": "apiKey", "in": "header", "name": "X-API-Key"}

        for path, methods in (schema.get("paths") or {}).items():
            for method_name, operation in methods.items():
                if (method_name.lower(), path) in PROTECTED_OPERATIONS and isinstance(operation, dict):
                    operation["security"] = [{"ApiKeyAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
