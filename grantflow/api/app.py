from __future__ import annotations

import io
import json
import tempfile
import uuid
import zipfile
from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from grantflow.api.public_views import public_checkpoint_payload, public_job_payload
from grantflow.api.schemas import HITLPendingListPublicResponse, JobStatusPublicResponse
from grantflow.api.security import (
    api_key_configured,
    install_openapi_api_key_security,
    read_auth_required,
    require_api_key_if_configured,
)
from grantflow.core.config import config
from grantflow.core.stores import create_job_store_from_env
from grantflow.core.strategies.factory import DonorFactory
from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc
from grantflow.memory_bank.ingest import ingest_pdf_to_namespace
from grantflow.memory_bank.vector_store import vector_store
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


install_openapi_api_key_security(app)


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


def _health_diagnostics() -> dict[str, Any]:
    job_store_mode = "sqlite" if getattr(JOB_STORE, "db_path", None) else "inmem"
    hitl_store_mode = "sqlite" if bool(getattr(hitl_manager, "_use_sqlite", False)) else "inmem"
    sqlite_path = getattr(JOB_STORE, "db_path", None) or (getattr(hitl_manager, "_sqlite_path", None) if hitl_store_mode == "sqlite" else None)

    vector_backend = "chroma" if getattr(vector_store, "client", None) is not None else "memory"
    diagnostics = {
        "job_store": {"mode": job_store_mode},
        "hitl_store": {"mode": hitl_store_mode},
        "auth": {
            "api_key_configured": bool(api_key_configured()),
            "read_auth_required": bool(read_auth_required()),
        },
        "vector_store": {
            "backend": vector_backend,
            "collection_prefix": getattr(vector_store, "prefix", "grantflow"),
        },
    }
    if sqlite_path and (job_store_mode == "sqlite" or hitl_store_mode == "sqlite"):
        diagnostics["sqlite"] = {"path": str(sqlite_path)}
    client_init_error = getattr(vector_store, "_client_init_error", None)
    if client_init_error:
        diagnostics["vector_store"]["client_init_error"] = str(client_init_error)
    return diagnostics


def _vector_store_readiness() -> dict[str, Any]:
    client = getattr(vector_store, "client", None)
    backend = "chroma" if client is not None else "memory"

    if backend == "memory":
        return {"ready": True, "backend": "memory", "reason": "in-memory fallback backend active"}

    try:
        heartbeat = getattr(client, "heartbeat", None)
        if callable(heartbeat):
            hb_value = heartbeat()
            return {"ready": True, "backend": "chroma", "heartbeat": str(hb_value)}

        # Fallback to a lightweight no-op-ish capability check if heartbeat() is unavailable.
        list_collections = getattr(client, "list_collections", None)
        if callable(list_collections):
            list_collections()
        return {"ready": True, "backend": "chroma"}
    except Exception as exc:
        return {"ready": False, "backend": "chroma", "error": str(exc)}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "diagnostics": _health_diagnostics()}


@app.get("/ready")
def readiness_check():
    vector_ready = _vector_store_readiness()
    ready = bool(vector_ready.get("ready"))
    payload = {
        "status": "ready" if ready else "degraded",
        "checks": {"vector_store": vector_ready},
    }
    if not ready:
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/donors")
def list_donors():
    return {"donors": DonorFactory.list_supported()}


@app.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks, request: Request):
    require_api_key_if_configured(request)
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
    require_api_key_if_configured(request)
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
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return public_job_payload(job)


@app.post("/hitl/approve")
def approve_checkpoint(req: HITLApprovalRequest, request: Request):
    require_api_key_if_configured(request)
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
    require_api_key_if_configured(request, for_read=True)
    pending = hitl_manager.list_pending(donor_id)
    return {
        "pending_count": len(pending),
        "checkpoints": [public_checkpoint_payload(cp) for cp in pending],
    }


@app.post("/ingest")
async def ingest_pdf(
    request: Request,
    donor_id: str = Form(...),
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

    namespace = strategy.get_rag_collection()
    upload_metadata: Dict[str, Any] = {
        "uploaded_filename": filename,
        "uploaded_content_type": content_type or "application/pdf",
        "donor_id": donor,
    }
    if metadata:
        upload_metadata.update(metadata)

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(prefix="grantflow_ingest_", suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        result = ingest_pdf_to_namespace(tmp_path, namespace=namespace, metadata=upload_metadata)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc
    finally:
        if tmp_path:
            try:
                import os

                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    return {
        "status": "ingested",
        "donor_id": donor,
        "namespace": namespace,
        "filename": filename,
        "result": result,
    }


@app.post("/export")
def export_artifacts(req: ExportRequest, request: Request):
    require_api_key_if_configured(request)
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
