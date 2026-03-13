from __future__ import annotations

import json
import tempfile
from typing import Any, Callable, Dict, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile

from grantflow.api.schemas import IngestInventoryPublicResponse, IngestRecentListPublicResponse

router = APIRouter()

_require_api_key_if_configured: Callable[..., None] | None = None
_resolve_tenant_id: Callable[..., Optional[str]] | None = None
_list_ingest_events: Callable[..., list[dict[str, Any]]] | None = None
_ingest_inventory_fn: Callable[..., list[dict[str, Any]]] | None = None
_portfolio_export_response: Callable[..., Any] | None = None
_public_ingest_recent_payload: Callable[..., dict[str, Any]] | None = None
_public_ingest_inventory_payload: Callable[..., dict[str, Any]] | None = None
_public_ingest_inventory_csv_text: Callable[..., str] | None = None
_donor_get_strategy: Callable[[str], Any] | None = None
_tenant_rag_namespace: Callable[[str, Optional[str]], str] | None = None
_vector_store_normalize_namespace: Callable[[str], str] | None = None
_ingest_pdf_to_namespace: Callable[..., Any] | None = None
_record_ingest_event: Callable[..., None] | None = None


def configure_ingest_router(
    *,
    require_api_key_if_configured: Callable[..., None],
    resolve_tenant_id: Callable[..., Optional[str]],
    list_ingest_events: Callable[..., list[dict[str, Any]]],
    ingest_inventory_fn: Callable[..., list[dict[str, Any]]],
    portfolio_export_response: Callable[..., Any],
    public_ingest_recent_payload: Callable[..., dict[str, Any]],
    public_ingest_inventory_payload: Callable[..., dict[str, Any]],
    public_ingest_inventory_csv_text: Callable[..., str],
    donor_get_strategy: Callable[[str], Any],
    tenant_rag_namespace: Callable[[str, Optional[str]], str],
    vector_store_normalize_namespace: Callable[[str], str],
    ingest_pdf_to_namespace_fn: Callable[..., Any],
    record_ingest_event: Callable[..., None],
) -> None:
    global _require_api_key_if_configured
    global _resolve_tenant_id
    global _list_ingest_events
    global _ingest_inventory_fn
    global _portfolio_export_response
    global _public_ingest_recent_payload
    global _public_ingest_inventory_payload
    global _public_ingest_inventory_csv_text
    global _donor_get_strategy
    global _tenant_rag_namespace
    global _vector_store_normalize_namespace
    global _ingest_pdf_to_namespace
    global _record_ingest_event

    _require_api_key_if_configured = require_api_key_if_configured
    _resolve_tenant_id = resolve_tenant_id
    _list_ingest_events = list_ingest_events
    _ingest_inventory_fn = ingest_inventory_fn
    _portfolio_export_response = portfolio_export_response
    _public_ingest_recent_payload = public_ingest_recent_payload
    _public_ingest_inventory_payload = public_ingest_inventory_payload
    _public_ingest_inventory_csv_text = public_ingest_inventory_csv_text
    _donor_get_strategy = donor_get_strategy
    _tenant_rag_namespace = tenant_rag_namespace
    _vector_store_normalize_namespace = vector_store_normalize_namespace
    _ingest_pdf_to_namespace = ingest_pdf_to_namespace_fn
    _record_ingest_event = record_ingest_event


@router.get("/ingest/recent", response_model=IngestRecentListPublicResponse, response_model_exclude_none=True)
def list_recent_ingests(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    _require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _list_ingest_events(donor_id=donor_id, tenant_id=resolved_tenant_id, limit=limit)
    return _public_ingest_recent_payload(rows, donor_id=(donor_id or None))


@router.get("/ingest/inventory", response_model=IngestInventoryPublicResponse, response_model_exclude_none=True)
def get_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
):
    _require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory_fn(donor_id=donor_id, tenant_id=resolved_tenant_id)
    return _public_ingest_inventory_payload(rows, donor_id=(donor_id or None))


@router.get("/ingest/inventory/export")
def export_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    format: Literal["csv", "json"] = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    _require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory_fn(donor_id=donor_id, tenant_id=resolved_tenant_id)
    payload = _public_ingest_inventory_payload(rows, donor_id=(donor_id or None))
    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_ingest_inventory",
        donor_id=donor_id,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_public_ingest_inventory_csv_text,
    )


@router.post("/ingest")
async def ingest_pdf(
    request: Request,
    donor_id: str = Form(...),
    tenant_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None),
):
    _require_api_key_if_configured(request)

    donor = (donor_id or "").strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = _donor_get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing uploaded file name")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    content_type = (file.content_type or "").lower().strip()
    allowed_content_types = {"", "application/pdf", "application/x-pdf", "application/octet-stream"}
    if content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")

    metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            parsed = json.loads(metadata_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="metadata_json must decode to an object")
        metadata = parsed

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    resolved_tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    namespace = _tenant_rag_namespace(strategy.get_rag_collection(), resolved_tenant_id)
    namespace_normalized = _vector_store_normalize_namespace(namespace)
    upload_metadata: Dict[str, Any] = {
        "uploaded_filename": filename,
        "uploaded_content_type": content_type or "application/pdf",
        "donor_id": donor,
        "namespace_normalized": namespace_normalized,
    }
    if resolved_tenant_id:
        upload_metadata["tenant_id"] = resolved_tenant_id
    if metadata:
        upload_metadata.update(metadata)

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(prefix="grantflow_ingest_", suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = _ingest_pdf_to_namespace(tmp_path, namespace=namespace, metadata=upload_metadata)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc
    finally:
        if tmp_path:
            try:
                import os

                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    result_payload = result if isinstance(result, dict) else {"raw_result": str(result)}
    _record_ingest_event(
        donor_id=donor,
        namespace=namespace,
        filename=filename,
        content_type=content_type or "application/pdf",
        metadata=upload_metadata,
        result=result_payload,
    )

    return {
        "status": "ingested",
        "donor_id": donor,
        "tenant_id": resolved_tenant_id,
        "namespace": namespace,
        "namespace_normalized": namespace_normalized,
        "filename": filename,
        "result": result_payload,
    }
