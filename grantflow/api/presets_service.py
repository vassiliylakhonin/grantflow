from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, HTTPException, Request
from pydantic import ValidationError

from grantflow.api.demo_presets import (
    list_generate_legacy_preset_details,
    list_generate_legacy_preset_summaries,
    list_ingest_preset_details,
    load_generate_legacy_preset,
)
from grantflow.api.schemas import GenerateFromPresetRequest, GenerateRequest
from grantflow.api.tenant import _resolve_tenant_id
from grantflow.core.strategies.factory import DonorFactory
from grantflow.eval.sample_presets import (
    available_sample_ids,
    build_generate_payload as build_sample_generate_payload,
    list_sample_preset_summaries,
    load_sample_payload,
)


def _dedupe_doc_families(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        out.append(token)
        seen.add(token)
    return out


def _generate_preset_rows_for_public() -> list[dict[str, Any]]:
    generate_presets: list[dict[str, Any]] = []
    for item in list_generate_legacy_preset_details():
        donor_id = str(item.get("donor_id") or "").strip().lower() or None
        title = str(item.get("title") or "").strip() or None
        donor_label = donor_id.upper() if donor_id else "LEGACY"
        generate_presets.append(
            {
                "preset_key": str(item.get("preset_key") or "").strip(),
                "donor_id": donor_id,
                "title": title,
                "label": f"{donor_label}: {title or str(item.get('preset_key') or '')}",
                "source_kind": "legacy",
                "source_file": None,
                "generate_payload": dict(item.get("generate_payload") or {}),
            }
        )
    for row in list_sample_preset_summaries():
        sample_id = str(row.get("sample_id") or "").strip()
        if not sample_id:
            continue
        try:
            payload = load_sample_payload(sample_id)
            generate_payload = build_sample_generate_payload(
                sample_id,
                llm_mode=True,
                hitl_enabled=True,
                architect_rag_enabled=True,
                strict_preflight=False,
            )
        except ValueError:
            continue
        donor_id = str(payload.get("donor_id") or row.get("donor_id") or "").strip().lower() or None
        title = str(row.get("title") or sample_id).strip() or sample_id
        donor_label = donor_id.upper() if donor_id else "RBM"
        generate_presets.append(
            {
                "preset_key": sample_id,
                "donor_id": donor_id,
                "title": title,
                "label": f"RBM ({donor_label}): {title}",
                "source_kind": "rbm",
                "source_file": row.get("source_file"),
                "generate_payload": generate_payload,
            }
        )
    return generate_presets


def _demo_preset_bundle_payload() -> dict[str, Any]:
    generate_presets = _generate_preset_rows_for_public()
    ingest_presets: list[dict[str, Any]] = []
    for item in list_ingest_preset_details():
        donor_id = str(item.get("donor_id") or "").strip().lower() or None
        title = str(item.get("title") or "").strip() or None
        donor_label = donor_id.upper() if donor_id else "INGEST"
        ingest_presets.append(
            {
                "preset_key": str(item.get("preset_key") or "").strip(),
                "donor_id": donor_id,
                "title": title,
                "label": f"{donor_label}: {title or str(item.get('preset_key') or '')}",
                "metadata": dict(item.get("metadata") or {}),
                "checklist_items": list(item.get("checklist_items") or []),
                "recommended_docs": list(item.get("recommended_docs") or []),
            }
        )
    return {
        "generate_presets": generate_presets,
        "ingest_presets": ingest_presets,
    }


def _resolve_preflight_request_context(
    *,
    request: Request,
    donor_id: str,
    tenant_id: Optional[str] = None,
    client_metadata: Optional[Dict[str, Any]] = None,
    input_context: Optional[Dict[str, Any]] = None,
    expected_doc_families: Optional[list[str]] = None,
) -> tuple[str, Any, Optional[Dict[str, Any]]]:
    donor = str(donor_id or "").strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metadata = dict(client_metadata) if isinstance(client_metadata, dict) else {}
    resolved_tenant_id = _resolve_tenant_id(
        request,
        explicit_tenant=tenant_id,
        client_metadata=metadata,
        require_if_enabled=True,
    )
    if resolved_tenant_id:
        metadata["tenant_id"] = resolved_tenant_id

    if isinstance(input_context, dict) and input_context:
        metadata["_preflight_input_context"] = dict(input_context)

    if isinstance(expected_doc_families, list):
        expected = _dedupe_doc_families(expected_doc_families)
        if expected:
            rag_readiness_raw = metadata.get("rag_readiness")
            rag_readiness: Dict[str, Any] = dict(rag_readiness_raw) if isinstance(rag_readiness_raw, dict) else {}
            rag_readiness["expected_doc_families"] = expected
            if not str(rag_readiness.get("donor_id") or "").strip():
                rag_readiness["donor_id"] = donor
            metadata["rag_readiness"] = rag_readiness

    return donor, strategy, (metadata or None)


def _resolve_generate_payload_from_preset(
    preset_key: str,
    *,
    preset_type: Literal["auto", "legacy", "rbm"],
) -> tuple[str, Dict[str, Any]]:
    token = str(preset_key or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Missing preset_key")

    legacy_error: Optional[str] = None
    rbm_error: Optional[str] = None

    if preset_type in {"auto", "legacy"}:
        try:
            legacy = load_generate_legacy_preset(token)
            payload = legacy.get("generate_payload")
            if not isinstance(payload, dict):
                raise HTTPException(status_code=500, detail=f"Preset '{token}' has invalid generate_payload")
            return "legacy", dict(payload)
        except ValueError as exc:
            legacy_error = str(exc)
            if preset_type == "legacy":
                raise HTTPException(status_code=404, detail=legacy_error) from exc

    if preset_type in {"auto", "rbm"}:
        try:
            sample_payload = load_sample_payload(token)
            default_llm_mode = bool(sample_payload.get("llm_mode", False))
            default_architect_rag = bool(sample_payload.get("architect_rag_enabled", False))
            return "rbm", build_sample_generate_payload(
                token,
                llm_mode=default_llm_mode,
                hitl_enabled=False,
                architect_rag_enabled=default_architect_rag,
                strict_preflight=False,
            )
        except ValueError as exc:
            rbm_error = str(exc)
            if preset_type == "rbm":
                raise HTTPException(status_code=404, detail=rbm_error) from exc

    legacy_keys = sorted(
        str(row.get("preset_key") or "").strip()
        for row in list_generate_legacy_preset_summaries()
        if isinstance(row, dict) and str(row.get("preset_key") or "").strip()
    )
    rbm_keys = available_sample_ids()
    raise HTTPException(
        status_code=404,
        detail={
            "reason": "generate_preset_not_found",
            "preset_key": token,
            "preset_type": preset_type,
            "legacy_error": legacy_error,
            "rbm_error": rbm_error,
            "available": {"legacy": legacy_keys, "rbm": rbm_keys},
        },
    )


def _build_generate_request_from_preset(req: GenerateFromPresetRequest) -> tuple[GenerateRequest, str]:
    preset_key = str(req.preset_key or "").strip()
    source_kind, base_payload = _resolve_generate_payload_from_preset(
        preset_key,
        preset_type=req.preset_type,
    )
    payload: Dict[str, Any] = dict(base_payload)

    input_context_raw = payload.get("input_context")
    input_context: Dict[str, Any] = dict(input_context_raw) if isinstance(input_context_raw, dict) else {}
    if isinstance(req.input_context_patch, dict) and req.input_context_patch:
        input_context.update(dict(req.input_context_patch))
    payload["input_context"] = input_context

    client_metadata_raw = payload.get("client_metadata")
    client_metadata: Dict[str, Any] = dict(client_metadata_raw) if isinstance(client_metadata_raw, dict) else {}
    if preset_key:
        client_metadata.setdefault("demo_generate_preset_key", preset_key)
    client_metadata.setdefault("demo_generate_preset_source", source_kind)
    if isinstance(req.client_metadata_patch, dict) and req.client_metadata_patch:
        client_metadata.update(dict(req.client_metadata_patch))
    payload["client_metadata"] = client_metadata

    if req.tenant_id is not None:
        payload["tenant_id"] = req.tenant_id
    if req.request_id is not None:
        payload["request_id"] = req.request_id
    if req.webhook_url is not None:
        payload["webhook_url"] = req.webhook_url
    if req.webhook_secret is not None:
        payload["webhook_secret"] = req.webhook_secret

    if req.llm_mode is not None:
        payload["llm_mode"] = bool(req.llm_mode)
    if req.architect_rag_enabled is not None:
        payload["architect_rag_enabled"] = bool(req.architect_rag_enabled)
    if req.require_grounded_generation is not None:
        payload["require_grounded_generation"] = bool(req.require_grounded_generation)
    if req.hitl_enabled is not None:
        payload["hitl_enabled"] = bool(req.hitl_enabled)
    if req.hitl_checkpoints is not None:
        payload["hitl_checkpoints"] = list(req.hitl_checkpoints)
    if req.strict_preflight is not None:
        payload["strict_preflight"] = bool(req.strict_preflight)

    try:
        return GenerateRequest(**payload), source_kind
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "reason": "invalid_generate_preset_payload",
                "preset_key": preset_key,
                "preset_source": source_kind,
                "errors": exc.errors(),
            },
        ) from exc


async def _dispatch_generate_from_preset(
    req: GenerateFromPresetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    *,
    request_id: Optional[str] = None,
):
    generate_req, source_kind = _build_generate_request_from_preset(req)
    from grantflow.api.routes.jobs import generate as generate_endpoint

    generated = await generate_endpoint(
        generate_req,
        background_tasks,
        request,
        request_id=request_id if request_id is not None else generate_req.request_id,
    )
    if isinstance(generated, dict):
        response = dict(generated)
        response["preset_key"] = str(req.preset_key or "").strip()
        response["preset_source"] = source_kind
        return response
    return generated
