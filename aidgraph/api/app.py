# aidgraph/api/app.py

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from aidgraph.core.config import config
from aidgraph.swarm.hitl import hitl_manager
from aidgraph.exporters.word_builder import build_docx_from_toc
from aidgraph.exporters.excel_builder import build_xlsx_from_logframe

app = FastAPI(
    title="AidGraph API",
    description="Enterprise-grade grant proposal automation",
    version="2.0.0"
)

class GenerateRequest(BaseModel):
    donor_id: str
    input_context: Dict[str, Any]
    llm_mode: bool = True
    hitl_enabled: bool = True

class HITLApprovalRequest(BaseModel):
    checkpoint_id: str
    approved: bool
    feedback: Optional[str] = None

class ExportRequest(BaseModel):
    toc_draft: Dict[str, Any]
    logframe_draft: Dict[str, Any]
    donor_id: str
    format: str = "both"

@app.get("/health")
def health_check():
    """Проверка здоровья API."""
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/donors")
def list_donors():
    """Возвращает список поддерживаемых доноров."""
    return {
        "donors": [
            {"id": "usaid", "name": "USAID", "rag_namespace": "usaid_ads201"},
            {"id": "eu", "name": "European Union", "rag_namespace": "eu_intpa"},
            {"id": "worldbank", "name": "World Bank", "rag_namespace": "worldbank_ads301"},
        ]
    }

@app.post("/generate")
def generate(req: GenerateRequest):
    """Запускает процесс генерации AidGraph."""
    try:
        initial_state = {
            "donor_id": req.donor_id,
            "input_context": req.input_context,
            "toc_draft": None,
            "logframe_draft": None,
            "critic_score": None,
            "iteration_count": 0,
            "max_iterations": config.graph.max_iterations,
            "errors": [],
        }
        
        result = initial_state
        
        if req.hitl_enabled and result.get("toc_draft"):
            checkpoint_id = hitl_manager.create_checkpoint("toc", result, req.donor_id)
            return {"status": "pending_hitl", "checkpoint_id": checkpoint_id, "state": result}
        
        return {"status": "completed", "state": result, "toc_draft": result.get("toc_draft")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hitl/approve")
def approve_checkpoint(req: HITLApprovalRequest):
    """Одобряет или отклоняет HITL точку."""
    checkpoint = hitl_manager.get_checkpoint(req.checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    if req.approved:
        hitl_manager.approve(req.checkpoint_id, req.feedback)
        return {"status": "approved", "checkpoint_id": req.checkpoint_id}
    else:
        hitl_manager.reject(req.checkpoint_id, req.feedback or "Rejected")
        return {"status": "rejected", "checkpoint_id": req.checkpoint_id}

@app.get("/hitl/pending")
def list_pending_hitl(donor_id: Optional[str] = None):
    """Возвращает список ожидающих HITL точек."""
    pending = hitl_manager.list_pending(donor_id)
    return {"pending_count": len(pending), "checkpoints": pending}

@app.post("/export")
def export_artifacts(req: ExportRequest):
    """Экспортирует ToC в .docx и LogFrame в .xlsx."""
    try:
        if req.format in ("docx", "both"):
            docx_bytes = build_docx_from_toc(req.toc_draft, req.donor_id)
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={req.donor_id}_toc.docx"}
            )
        if req.format in ("xlsx", "both"):
            xlsx_bytes = build_xlsx_from_logframe(req.logframe_draft, req.donor_id)
            return Response(
                content=xlsx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={req.donor_id}_logframe.xlsx"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.api_host, port=config.api_port, reload=config.debug)
