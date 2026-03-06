from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse

from grantflow.api.demo_presets import (
    list_generate_legacy_preset_summaries,
    load_generate_legacy_preset,
)
from grantflow.api.demo_ui import render_demo_ui_html
from grantflow.api.presets_service import _demo_preset_bundle_payload, _generate_preset_rows_for_public
from grantflow.api.routers import presets_router
from grantflow.api.schemas import (
    DemoGeneratePresetPublicResponse,
    DemoPresetBundlePublicResponse,
    GenerateLegacyPresetDetailPublicResponse,
    GenerateLegacyPresetListPublicResponse,
    GeneratePresetListPublicResponse,
    RBMSamplePresetDetailPublicResponse,
    RBMSamplePresetListPublicResponse,
)
from grantflow.core.strategies.factory import DonorFactory
from grantflow.eval.sample_presets import (
    build_generate_payload as build_sample_generate_payload,
    list_sample_preset_summaries,
    load_sample_payload,
)


@presets_router.get("/donors")
def list_donors():
    return {"donors": DonorFactory.list_supported()}


@presets_router.get(
    "/demo/presets",
    response_model=DemoPresetBundlePublicResponse,
    response_model_exclude_none=True,
)
def get_demo_presets():
    return _demo_preset_bundle_payload()


@presets_router.get(
    "/generate/presets",
    response_model=GeneratePresetListPublicResponse,
    response_model_exclude_none=True,
)
def list_generate_presets():
    return {"presets": _generate_preset_rows_for_public()}


@presets_router.get(
    "/generate/presets/legacy",
    response_model=GenerateLegacyPresetListPublicResponse,
    response_model_exclude_none=True,
)
def list_generate_legacy_presets():
    return {"presets": list_generate_legacy_preset_summaries()}


@presets_router.get(
    "/generate/presets/legacy/{preset_key}",
    response_model=GenerateLegacyPresetDetailPublicResponse,
    response_model_exclude_none=True,
)
def get_generate_legacy_preset(preset_key: str):
    try:
        return load_generate_legacy_preset(preset_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@presets_router.get(
    "/generate/presets/rbm",
    response_model=RBMSamplePresetListPublicResponse,
    response_model_exclude_none=True,
)
def list_rbm_generate_presets():
    return {"presets": list_sample_preset_summaries()}


@presets_router.get(
    "/generate/presets/rbm/{sample_id}",
    response_model=RBMSamplePresetDetailPublicResponse,
    response_model_exclude_none=True,
)
def get_rbm_generate_preset(
    sample_id: str,
    llm_mode: bool = Query(default=False),
    hitl_enabled: bool = Query(default=False),
    architect_rag_enabled: bool = Query(default=False),
    strict_preflight: bool = Query(default=False),
):
    try:
        payload = load_sample_payload(sample_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    source_file = None
    normalized = str(sample_id or "").strip().lower()
    for row in list_sample_preset_summaries():
        if str(row.get("sample_id") or "").strip().lower() == normalized:
            source_file = row.get("source_file")
            break

    return {
        "sample_id": normalized,
        "source_file": source_file,
        "payload": payload,
        "generate_payload": build_sample_generate_payload(
            normalized,
            llm_mode=bool(llm_mode),
            hitl_enabled=bool(hitl_enabled),
            architect_rag_enabled=bool(architect_rag_enabled),
            strict_preflight=bool(strict_preflight),
        ),
    }


@presets_router.get(
    "/generate/presets/{preset_key}",
    response_model=DemoGeneratePresetPublicResponse,
    response_model_exclude_none=True,
)
def get_generate_preset(
    preset_key: str,
    llm_mode: Optional[bool] = Query(default=None),
    hitl_enabled: Optional[bool] = Query(default=None),
    architect_rag_enabled: Optional[bool] = Query(default=None),
    strict_preflight: Optional[bool] = Query(default=None),
):
    token = str(preset_key or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Missing preset_key")

    target = None
    for row in _generate_preset_rows_for_public():
        if not isinstance(row, dict):
            continue
        if str(row.get("preset_key") or "").strip() == token:
            target = dict(row)
            break

    if target is None:
        available = sorted(
            str(row.get("preset_key") or "").strip()
            for row in _generate_preset_rows_for_public()
            if isinstance(row, dict) and str(row.get("preset_key") or "").strip()
        )
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "generate_preset_not_found",
                "preset_key": token,
                "available": available,
            },
        )

    generate_payload = dict(target.get("generate_payload") or {})
    if llm_mode is not None:
        generate_payload["llm_mode"] = bool(llm_mode)
    if hitl_enabled is not None:
        generate_payload["hitl_enabled"] = bool(hitl_enabled)
    if architect_rag_enabled is not None:
        generate_payload["architect_rag_enabled"] = bool(architect_rag_enabled)
    if strict_preflight is not None:
        generate_payload["strict_preflight"] = bool(strict_preflight)
    target["generate_payload"] = generate_payload
    return target


@presets_router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_console():
    return HTMLResponse(render_demo_ui_html())
