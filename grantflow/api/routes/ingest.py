from __future__ import annotations

import json
import tempfile
from typing import Any, Dict, Optional

from fastapi import File, Form, HTTPException, Query, Request, UploadFile

from grantflow.api import app as api_app_module
from grantflow.api.app import (
    _ingest_inventory,
    _list_ingest_events,
    _record_ingest_event,
)
from grantflow.api.demo_presets import list_ingest_preset_summaries, load_ingest_preset
from grantflow.api.presets_service import _resolve_preflight_request_context
from grantflow.api.public_views import public_ingest_inventory_payload, public_ingest_recent_payload
from grantflow.api.schemas import (
    GeneratePreflightPublicResponse,
    IngestInventoryPublicResponse,
    IngestPresetDetailPublicResponse,
    IngestPresetListPublicResponse,
    IngestReadinessRequest,
    IngestRecentListPublicResponse,
)
from grantflow.api.security import require_api_key_if_configured
from grantflow.api.tenant import _resolve_tenant_id, _tenant_rag_namespace
from grantflow.api.routers import ingest_router
from grantflow.core.strategies.factory import DonorFactory
from grantflow.memory_bank.vector_store import vector_store


@ingest_router.get(
    "/ingest/presets",
    response_model=IngestPresetListPublicResponse,
    response_model_exclude_none=True,
)
def list_ingest_presets():
    return {"presets": list_ingest_preset_summaries()}


@ingest_router.get(
    "/ingest/presets/{preset_key}",
    response_model=IngestPresetDetailPublicResponse,
    response_model_exclude_none=True,
)
def get_ingest_preset(preset_key: str):
    try:
        return load_ingest_preset(preset_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@ingest_router.post(
    "/ingest/readiness",
    response_model=GeneratePreflightPublicResponse,
    response_model_exclude_none=True,
)
def ingest_readiness(req: IngestReadinessRequest, request: Request):
    require_api_key_if_configured(request, for_read=True)
    donor, strategy, client_metadata = _resolve_preflight_request_context(
        request=request,
        donor_id=req.donor_id,
        tenant_id=req.tenant_id,
        client_metadata=req.client_metadata,
        input_context=req.input_context,
        expected_doc_families=req.expected_doc_families,
    )
    return api_app_module._build_generate_preflight(
        donor_id=donor,
        strategy=strategy,
        client_metadata=client_metadata,
        architect_rag_enabled=bool(req.architect_rag_enabled),
    )


@ingest_router.get("/ingest/recent", response_model=IngestRecentListPublicResponse, response_model_exclude_none=True)
def list_recent_ingests(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _list_ingest_events(donor_id=donor_id, tenant_id=resolved_tenant_id, limit=limit)
    return public_ingest_recent_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)


@ingest_router.get("/ingest/inventory", response_model=IngestInventoryPublicResponse, response_model_exclude_none=True)
def get_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory(donor_id=donor_id, tenant_id=resolved_tenant_id)
    return public_ingest_inventory_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)


@ingest_router.post("/ingest")
async def ingest_pdf(
    request: Request,
    donor_id: str = Form(...),
    tenant_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None),
):
    require_api_key_if_configured(request)

    donor = (donor_id or "").strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = DonorFactory.get_strategy(donor)
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
    namespace_normalized = vector_store.normalize_namespace(namespace)
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
        result = api_app_module.ingest_pdf_to_namespace(tmp_path, namespace=namespace, metadata=upload_metadata)
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
