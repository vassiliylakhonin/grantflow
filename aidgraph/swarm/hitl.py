# aidgraph/swarm/hitl.py

from __future__ import annotations

from typing import Dict, Any, Optional, Literal
from enum import Enum
import uuid

class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"

class HITLCheckpoint:
    """
    Менеджер точек Human-in-the-Loop.
    """
    
    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
    
    def create_checkpoint(
        self, 
        stage: Literal["toc", "logframe"],
        state: Dict[str, Any],
        donor_id: str
    ) -> str:
        """Создаёт новую HITL точку."""
        checkpoint_id = str(uuid.uuid4())
        self._checkpoints[checkpoint_id] = {
            "id": checkpoint_id,
            "stage": stage,
            "status": HITLStatus.PENDING,
            "state_snapshot": state,
            "donor_id": donor_id,
            "feedback": None,
        }
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Получает HITL точку по ID."""
        return self._checkpoints.get(checkpoint_id)
    
    def approve(self, checkpoint_id: str, feedback: Optional[str] = None) -> bool:
        """Одобряет HITL точку."""
        if checkpoint_id not in self._checkpoints:
            return False
        self._checkpoints[checkpoint_id]["status"] = HITLStatus.APPROVED
        self._checkpoints[checkpoint_id]["feedback"] = feedback
        return True
    
    def reject(self, checkpoint_id: str, feedback: str) -> bool:
        """Отклоняет HITL точку с комментарием."""
        if checkpoint_id not in self._checkpoints:
            return False
        self._checkpoints[checkpoint_id]["status"] = HITLStatus.REJECTED
        self._checkpoints[checkpoint_id]["feedback"] = feedback
        return True
    
    def is_approved(self, checkpoint_id: str) -> bool:
        """Проверяет, одобрена ли точка."""
        checkpoint = self._checkpoints.get(checkpoint_id)
        return checkpoint is not None and checkpoint["status"] == HITLStatus.APPROVED
    
    def list_pending(self, donor_id: Optional[str] = None) -> list:
        """Возвращает список ожидающих точек."""
        pending = []
        for cp in self._checkpoints.values():
            if cp["status"] == HITLStatus.PENDING:
                if donor_id is None or cp["donor_id"] == donor_id:
                    pending.append(cp)
        return pending

hitl_manager = HITLCheckpoint()
