# grantflow/swarm/hitl.py

from __future__ import annotations

import copy
import uuid
from enum import Enum
from typing import Any, Dict, Literal, Optional


class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class HITLCheckpoint:
    """In-memory manager for Human-in-the-Loop checkpoints."""

    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

    def create_checkpoint(
        self,
        stage: Literal["toc", "logframe"],
        state: Dict[str, Any],
        donor_id: str,
    ) -> str:
        """Creates a new HITL checkpoint with a state snapshot for auditability."""
        checkpoint_id = str(uuid.uuid4())
        self._checkpoints[checkpoint_id] = {
            "id": checkpoint_id,
            "stage": stage,
            "status": HITLStatus.PENDING,
            "state_snapshot": copy.deepcopy(state),
            "donor_id": donor_id,
            "feedback": None,
        }
        return checkpoint_id

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        return self._checkpoints.get(checkpoint_id)

    def approve(self, checkpoint_id: str, feedback: Optional[str] = None) -> bool:
        if checkpoint_id not in self._checkpoints:
            return False
        self._checkpoints[checkpoint_id]["status"] = HITLStatus.APPROVED
        self._checkpoints[checkpoint_id]["feedback"] = feedback
        return True

    def reject(self, checkpoint_id: str, feedback: str) -> bool:
        if checkpoint_id not in self._checkpoints:
            return False
        self._checkpoints[checkpoint_id]["status"] = HITLStatus.REJECTED
        self._checkpoints[checkpoint_id]["feedback"] = feedback
        return True

    def is_approved(self, checkpoint_id: str) -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        return checkpoint is not None and checkpoint["status"] == HITLStatus.APPROVED

    def list_pending(self, donor_id: Optional[str] = None) -> list:
        pending = []
        for cp in self._checkpoints.values():
            if cp["status"] == HITLStatus.PENDING:
                if donor_id is None or cp["donor_id"] == donor_id:
                    pending.append(cp)
        return pending


hitl_manager = HITLCheckpoint()
