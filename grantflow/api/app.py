from __future__ import annotations

import io
import os
import secrets
import uuid
import zipfile
from enum import Enum
from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from grantflow.core.config import config
from grantflow.core.stores import create_job_store_from_env
from grantflow.core.strategies.factory import DonorFactory
from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc
from grantflow.swarm.graph import grantflow_graph
from grantflow.swarm.hitl import HITLStatus, hitl_manager
from grantflow.swarm.nodes.architect import draft_toc
from grantflow.swarm.nodes.critic import red_team_critic
from grantflow.swarm.nodes.discovery import validate_input_richness
from grantflow.swarm.nodes.mel_specialist import mel_assign_indicators

app = FastAPI(
    title="GrantFlow API",
    description="Enterprise-grade grant proposal automation",
    version="2.0.0",
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

JOB_STORE = create_job_store_from_env()

HITLStartAt = Literal["start", "architect", "mel", "critic"]


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    JOB_STORE.set(job_id, payload)


def _update_job(job_id: str, **patch: Any) -> Dict[str, Any]:
    return JOB_STORE.update(job_id, **patch)


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return JOB_STORE.get(job_id)


class GenerateRequest(BaseModel):
    donor_id: str
    input_context: Dict[str, Any]
    llm_mode: bool = False
    hitl_enabled: bool = False

    model_config = ConfigDict(extra="forbid")


class HITLApprovalRequest(BaseModel):
    checkpoint_id: str
    approved: bool
    feedback: Optional[str] = None


class ExportRequest(BaseModel):
    payload: Optional[Dict[str, Any]] = None
    toc_draft: Optional[Dict[str, Any]] = None
    logframe_draft: Optional[Dict[str, Any]] = None
    donor_id: Optional[str] = None
    format: str = "both"

    model_config = ConfigDict(extra="allow")


class JobStatusPublicResponse(BaseModel):
    status: str
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    checkpoint_id: Optional[str] = None
    checkpoint_stage: Optional[str] = None
    checkpoint_status: Optional[str] = None
    resume_from: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class HITLPendingCheckpointPublicResponse(BaseModel):
    id: str
    stage: str
    status: str
    donor_id: str
    feedback: Optional[str] = None
    has_state_snapshot: bool

    model_config = ConfigDict(extra="allow")


class HITLPendingListPublicResponse(BaseModel):
    pending_count: int
    checkpoints: list[HITLPendingCheckpointPublicResponse]

    model_config = ConfigDict(extra="allow")


def _resolve_export_inputs(req: ExportRequest) -> tuple[dict, dict, str]:
    payload = req.payload or {}
    if isinstance(payload.get("state"), dict):
        payload = payload["state"]

    donor_id = req.donor_id or payload.get("donor") or payload.get("donor_id") or "grantflow"
    toc = req.toc_draft or payload.get("toc_draft") or payload.get("toc") or {}
    logframe = req.logframe_draft or payload.get("logframe_draft") or payload.get("mel") or {}

    if not isinstance(toc, dict):
        toc = {}
    if not isinstance(logframe, dict):
        logframe = {}
    return toc, logframe, str(donor_id)


def _record_hitl_feedback_in_state(state: dict, checkpoint: Dict[str, Any]) -> None:
    feedback = checkpoint.get("feedback")
    if not feedback:
        return
    history = list(state.get("hitl_feedback_history") or [])
    history.append(
        {
            "checkpoint_id": checkpoint.get("id"),
            "stage": checkpoint.get("stage"),
            "status": getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
            "feedback": feedback,
        }
    )
    state["hitl_feedback_history"] = history
    state["hitl_feedback"] = feedback


def _api_key_configured() -> str | None:
    return os.getenv("GRANTFLOW_API_KEY") or os.getenv("API_KEY")


def _read_auth_required() -> bool:
    return (os.getenv("GRANTFLOW_REQUIRE_AUTH_FOR_READS", "false").strip().lower() == "true")


def _require_api_key_if_configured(request: Request, *, for_read: bool = False) -> None:
    expected = _api_key_configured()
    if not expected:
        return
    if for_read and not _read_auth_required():
        return

    provided = request.headers.get("x-api-key")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _install_openapi_api_key_security() -> None:
    protected_operations = {
        ("post", "/generate"),
        ("post", "/resume/{job_id}"),
        ("post", "/hitl/approve"),
        ("post", "/export"),
        ("get", "/status/{job_id}"),
        ("get", "/hitl/pending"),
    }

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
                if (method_name.lower(), path) in protected_operations and isinstance(operation, dict):
                    operation["security"] = [{"ApiKeyAuth": []}]

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


_install_openapi_api_key_security()


def _sanitize_for_public_response(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _sanitize_for_public_response(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_public_response(item) for item in value]
    return str(value)


def _public_state_snapshot(state: Any) -> Any:
    if not isinstance(state, dict):
        return _sanitize_for_public_response(state)

    redacted_state = {}
    for key, value in state.items():
        if key in {"strategy", "donor_strategy"}:
            continue
        redacted_state[str(key)] = _sanitize_for_public_response(value)
    return redacted_state


def _public_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    public_job: Dict[str, Any] = {}
    for key, value in job.items():
        if key == "state":
            public_job[key] = _public_state_snapshot(value)
            continue
        public_job[str(key)] = _sanitize_for_public_response(value)
    return public_job


def _public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = _sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint


def _pause_for_hitl(job_id: str, state: dict, stage: Literal["toc", "logframe"], resume_from: HITLStartAt) -> None:
    donor_id = state.get("donor") or state.get("donor_id") or "unknown"
    checkpoint_id = hitl_manager.create_checkpoint(stage, state, donor_id)
    _set_job(
        job_id,
        {
            "status": "pending_hitl",
            "state": state,
            "checkpoint_id": checkpoint_id,
            "checkpoint_stage": stage,
            "resume_from": resume_from,
            "hitl_enabled": True,
        },
    )


def _run_pipeline_to_completion(job_id: str, initial_state: dict) -> None:
    try:
        _set_job(job_id, {"status": "running", "state": initial_state, "hitl_enabled": False})
        final_state = grantflow_graph.invoke(initial_state)
        _set_job(job_id, {"status": "done", "state": final_state, "hitl_enabled": False})
    except Exception as exc:
        _set_job(job_id, {"status": "error", "error": str(exc), "hitl_enabled": False})


def _run_hitl_pipeline(job_id: str, state: dict, start_at: HITLStartAt) -> None:
    try:
        _set_job(
            job_id,
            {
                "status": "running",
                "state": state,
                "hitl_enabled": True,
                "resume_from": start_at,
            },
        )

        if start_at == "start":
            state = validate_input_richness(state)
            state = draft_toc(state)
            _pause_for_hitl(job_id, state, stage="toc", resume_from="mel")
            return

        if start_at == "architect":
            state = draft_toc(state)
            _pause_for_hitl(job_id, state, stage="toc", resume_from="mel")
            return

        if start_at == "mel":
            state = mel_assign_indicators(state)
            _pause_for_hitl(job_id, state, stage="logframe", resume_from="critic")
            return

        if start_at == "critic":
            state = red_team_critic(state)
            if state.get("needs_revision"):
                # Re-enter review cycle with a fresh ToC checkpoint.
                state = draft_toc(state)
                _pause_for_hitl(job_id, state, stage="toc", resume_from="mel")
                return
            _set_job(job_id, {"status": "done", "state": state, "hitl_enabled": True})
            return

        raise ValueError(f"Unsupported start_at: {start_at}")
    except Exception as exc:
        _set_job(job_id, {"status": "error", "error": str(exc), "hitl_enabled": True, "state": state})


def _resume_target_from_checkpoint(checkpoint: Dict[str, Any], default_resume_from: str | None) -> HITLStartAt:
    stage = checkpoint.get("stage")
    status = checkpoint.get("status")

    if status == HITLStatus.APPROVED:
        if stage == "toc":
            return "mel"
        if stage == "logframe":
            return "critic"

    if status == HITLStatus.REJECTED:
        if stage == "toc":
            return "architect"
        if stage == "logframe":
            return "mel"

    if default_resume_from in {"start", "architect", "mel", "critic"}:
        return default_resume_from  # type: ignore[return-value]

    raise ValueError("Checkpoint is not ready for resume")


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/donors")
def list_donors():
    return {"donors": DonorFactory.list_supported()}


@app.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks, request: Request):
    _require_api_key_if_configured(request)
    donor = req.donor_id.strip()
    if not donor:
        raise HTTPException(status_code=400, detail="Missing donor_id")

    try:
        strategy = DonorFactory.get_strategy(donor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    input_payload = req.input_context or {}
    job_id = str(uuid.uuid4())
    initial_state = {
        "donor": donor,
        "donor_id": donor,
        "donor_strategy": strategy,
        "strategy": strategy,
        "input": input_payload,
        "input_context": input_payload,
        "llm_mode": req.llm_mode,
        "iteration": 0,
        "iteration_count": 0,
        "max_iterations": config.graph.max_iterations,
        "quality_score": 0.0,
        "critic_score": 0.0,
        "needs_revision": False,
        "critic_notes": [],
        "critic_feedback_history": [],
        "hitl_pending": False,
        "errors": [],
    }

    _set_job(job_id, {"status": "accepted", "state": initial_state, "hitl_enabled": req.hitl_enabled})
    if req.hitl_enabled:
        background_tasks.add_task(_run_hitl_pipeline, job_id, initial_state, "start")
    else:
        background_tasks.add_task(_run_pipeline_to_completion, job_id, initial_state)
    return {"status": "accepted", "job_id": job_id}


@app.post("/resume/{job_id}")
async def resume_job(job_id: str, background_tasks: BackgroundTasks, request: Request):
    _require_api_key_if_configured(request)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "pending_hitl":
        raise HTTPException(status_code=409, detail="Job is not waiting for HITL review")

    checkpoint_id = job.get("checkpoint_id")
    if not checkpoint_id:
        raise HTTPException(status_code=409, detail="Checkpoint missing for pending HITL job")

    checkpoint = hitl_manager.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if checkpoint.get("status") == HITLStatus.PENDING:
        raise HTTPException(status_code=409, detail="Checkpoint is still pending approval")

    state = job.get("state")
    if not isinstance(state, dict):
        raise HTTPException(status_code=409, detail="Job state is missing or invalid")

    _record_hitl_feedback_in_state(state, checkpoint)

    try:
        start_at = _resume_target_from_checkpoint(checkpoint, job.get("resume_from"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _update_job(job_id, status="accepted", state=state, resume_from=start_at, checkpoint_status=getattr(checkpoint.get("status"), "value", checkpoint.get("status")))
    background_tasks.add_task(_run_hitl_pipeline, job_id, state, start_at)
    return {
        "status": "accepted",
        "job_id": job_id,
        "resuming_from": start_at,
        "checkpoint_id": checkpoint_id,
        "checkpoint_status": getattr(checkpoint.get("status"), "value", checkpoint.get("status")),
    }


@app.get("/status/{job_id}", response_model=JobStatusPublicResponse, response_model_exclude_none=True)
def get_status(job_id: str, request: Request):
    _require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job_payload(job)


@app.post("/hitl/approve")
def approve_checkpoint(req: HITLApprovalRequest, request: Request):
    _require_api_key_if_configured(request)
    checkpoint = hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if req.approved:
        hitl_manager.approve(req.checkpoint_id, req.feedback)
        return {"status": "approved", "checkpoint_id": req.checkpoint_id}

    hitl_manager.reject(req.checkpoint_id, req.feedback or "Rejected")
    return {"status": "rejected", "checkpoint_id": req.checkpoint_id}


@app.get("/hitl/pending", response_model=HITLPendingListPublicResponse, response_model_exclude_none=True)
def list_pending_hitl(request: Request, donor_id: Optional[str] = None):
    _require_api_key_if_configured(request, for_read=True)
    pending = hitl_manager.list_pending(donor_id)
    return {
        "pending_count": len(pending),
        "checkpoints": [_public_checkpoint_payload(cp) for cp in pending],
    }


@app.post("/export")
def export_artifacts(req: ExportRequest, request: Request):
    _require_api_key_if_configured(request)
    toc_draft, logframe_draft, donor_id = _resolve_export_inputs(req)
    fmt = (req.format or "").lower()

    try:
        docx_bytes: Optional[bytes] = None
        xlsx_bytes: Optional[bytes] = None

        if fmt in {"docx", "both"}:
            docx_bytes = build_docx_from_toc(toc_draft, donor_id)

        if fmt in {"xlsx", "both"}:
            xlsx_bytes = build_xlsx_from_logframe(logframe_draft, donor_id)

        if fmt == "docx" and docx_bytes is not None:
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": "attachment; filename=proposal.docx"},
            )

        if fmt == "xlsx" and xlsx_bytes is not None:
            return StreamingResponse(
                io.BytesIO(xlsx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=mel.xlsx"},
            )

        if fmt == "both" and docx_bytes is not None and xlsx_bytes is not None:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("proposal.docx", docx_bytes)
                archive.writestr("mel.xlsx", xlsx_bytes)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=grantflow_export.zip"},
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="Unsupported format")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
