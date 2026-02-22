# aidgraph/api/app.py
from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
import uuid

from aidgraph.core.config import config
from aidgraph.swarm.hitl import hitl_manager
from aidgraph.exporters.word_builder import build_docx_from_toc
from aidgraph.exporters.excel_builder import build_xlsx_from_logframe
from aidgraph.swarm.graph import aidgraph_graph
from aidgraph.core.strategies.factory import DonorFactory

app = FastAPI(
    title="AidGraph API",
    description="Enterprise-grade grant proposal automation",
    version="2.0.0"
)

# Простая in-memory база для отслеживания статуса долгих задач
# (в проде лучше использовать Redis или Celery)
JOB_STATUS_DB = {}

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
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Принимает запрос, валидирует донора и запускает процесс генерации AidGraph в фоне.
    Возвращает job_id для отслеживания статуса.
    """
    try:
        # 1. Валидируем донора через Фабрику
        strategy = DonorFactory.get_strategy(req.donor_id)
        if not strategy:
            raise HTTPException(status_code=400, detail=f"Unsupported donor_id: {req.donor_id}")
        
        # 2. Генерируем уникальный ID задачи
        job_id = str(uuid.uuid4())
        
        # 3. Собираем начальное состояние
        initial_state = {
            "donor_id": req.donor_id,
            "donor_strategy": strategy,  # Инжектим саму стратегию в стейт!
            "input_context": req.input_context,
            "toc_draft": None,
            "logframe_draft": None,
            "critic_score": None,
            "critic_feedback_history": [],
            "iteration_count": 0,
            "max_iterations": config.graph.max_iterations,
            "errors": [],
        }
        
        # Записываем статус "в работе"
        JOB_STATUS_DB[job_id] = {"status": "processing", "state": None}
        
        # 4. Функция-воркер для фонового запуска
        def run_graph_task(job_id: str, state: dict):
            try:
                # ВОТ ЗДЕСЬ мы реально запускаем рой агентов (LangGraph)
                final_state = aidgraph_graph.invoke(state)
                
                # Если нужна проверка HITL после графа
                if req.hitl_enabled and final_state.get("toc_draft"):
                    checkpoint_id = hitl_manager.create_checkpoint("toc", final_state, req.donor_id)
                    JOB_STATUS_DB[job_id] = {"status": "pending_hitl", "checkpoint_id": checkpoint_id}
                else:
                    JOB_STATUS_DB[job_id] = {"status": "completed", "state": final_state}
            except Exception as e:
                JOB_STATUS_DB[job_id] = {"status": "failed", "error": str(e)}
        
        # 5. Отправляем задачу в фон, чтобы не блокировать API
        background_tasks.add_task(run_graph_task, job_id, initial_state)
        
        return {"status": "accepted", "job_id": job_id, "message": "Proposal generation started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Позволяет фронтенду поллить статус генерации."""
    job = JOB_STATUS_DB.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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
