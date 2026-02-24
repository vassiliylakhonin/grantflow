# grantflow/swarm/hitl.py

from __future__ import annotations

import copy
import sqlite3
import threading
import uuid
from enum import Enum
from typing import Any, Dict, Literal, Optional

from grantflow.core.stores import (
    _env,
    default_sqlite_path,
    ensure_sqlite_component_schema,
    open_sqlite_connection,
    prepare_state_for_storage,
    storage_json_dumps,
    storage_json_loads,
    storage_mode,
)


class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
    CANCELED = "canceled"


class HITLCheckpoint:
    """In-memory manager for Human-in-the-Loop checkpoints."""
    SCHEMA_COMPONENT = "hitl_checkpoints"
    SCHEMA_VERSION = 1

    def __init__(self):
        mode = storage_mode(
            "GRANTFLOW_HITL_STORE",
            _env("HITL_STORE", storage_mode("GRANTFLOW_JOB_STORE", _env("JOB_STORE", "inmem"))),
        )
        self._use_sqlite = mode == "sqlite"
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._sqlite_path = default_sqlite_path()
        if self._use_sqlite:
            self._init_sqlite()

    def _connect(self) -> sqlite3.Connection:
        return open_sqlite_connection(self._sqlite_path)

    def _init_sqlite(self) -> None:
        with self._connect() as conn:
            ensure_sqlite_component_schema(conn, self.SCHEMA_COMPONENT, self.SCHEMA_VERSION)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_checkpoints (
                  id TEXT PRIMARY KEY,
                  stage TEXT NOT NULL,
                  status TEXT NOT NULL,
                  donor_id TEXT NOT NULL,
                  feedback TEXT,
                  state_snapshot_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _row_to_checkpoint(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "stage": row["stage"],
            "status": HITLStatus(row["status"]) if row["status"] in HITLStatus._value2member_map_ else row["status"],
            "state_snapshot": storage_json_loads(row["state_snapshot_json"]),
            "donor_id": row["donor_id"],
            "feedback": row["feedback"],
        }

    def create_checkpoint(
        self,
        stage: Literal["toc", "logframe"],
        state: Dict[str, Any],
        donor_id: str,
    ) -> str:
        """Creates a new HITL checkpoint with a state snapshot for auditability."""
        checkpoint_id = str(uuid.uuid4())
        if self._use_sqlite:
            snapshot_json = storage_json_dumps(prepare_state_for_storage(state))
            with self._lock:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO hitl_checkpoints (id, stage, status, donor_id, feedback, state_snapshot_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (checkpoint_id, stage, HITLStatus.PENDING.value, donor_id, None, snapshot_json),
                    )
            return checkpoint_id

        with self._lock:
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
        if self._use_sqlite:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM hitl_checkpoints WHERE id = ?", (checkpoint_id,)).fetchone()
            return self._row_to_checkpoint(row) if row is not None else None

        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            return copy.deepcopy(checkpoint) if checkpoint is not None else None

    def approve(self, checkpoint_id: str, feedback: Optional[str] = None) -> bool:
        if self._use_sqlite:
            with self._lock:
                with self._connect() as conn:
                    cur = conn.execute(
                        """
                        UPDATE hitl_checkpoints
                        SET status = ?, feedback = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (HITLStatus.APPROVED.value, feedback, checkpoint_id),
                    )
                    return cur.rowcount > 0

        with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False
            self._checkpoints[checkpoint_id]["status"] = HITLStatus.APPROVED
            self._checkpoints[checkpoint_id]["feedback"] = feedback
            return True

    def reject(self, checkpoint_id: str, feedback: str) -> bool:
        if self._use_sqlite:
            with self._lock:
                with self._connect() as conn:
                    cur = conn.execute(
                        """
                        UPDATE hitl_checkpoints
                        SET status = ?, feedback = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (HITLStatus.REJECTED.value, feedback, checkpoint_id),
                    )
                    return cur.rowcount > 0

        with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False
            self._checkpoints[checkpoint_id]["status"] = HITLStatus.REJECTED
            self._checkpoints[checkpoint_id]["feedback"] = feedback
            return True

    def cancel(self, checkpoint_id: str, feedback: Optional[str] = None) -> bool:
        if self._use_sqlite:
            with self._lock:
                with self._connect() as conn:
                    cur = conn.execute(
                        """
                        UPDATE hitl_checkpoints
                        SET status = ?, feedback = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (HITLStatus.CANCELED.value, feedback, checkpoint_id),
                    )
                    return cur.rowcount > 0

        with self._lock:
            if checkpoint_id not in self._checkpoints:
                return False
            self._checkpoints[checkpoint_id]["status"] = HITLStatus.CANCELED
            self._checkpoints[checkpoint_id]["feedback"] = feedback
            return True

    def is_approved(self, checkpoint_id: str) -> bool:
        if self._use_sqlite:
            with self._connect() as conn:
                row = conn.execute("SELECT status FROM hitl_checkpoints WHERE id = ?", (checkpoint_id,)).fetchone()
            return row is not None and row["status"] == HITLStatus.APPROVED.value

        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            return checkpoint is not None and checkpoint["status"] == HITLStatus.APPROVED

    def list_pending(self, donor_id: Optional[str] = None) -> list:
        if self._use_sqlite:
            query = "SELECT * FROM hitl_checkpoints WHERE status = ?"
            params: list[Any] = [HITLStatus.PENDING.value]
            if donor_id is not None:
                query += " AND donor_id = ?"
                params.append(donor_id)
            query += " ORDER BY updated_at DESC"
            with self._connect() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_checkpoint(row) for row in rows]

        with self._lock:
            pending = []
            for cp in self._checkpoints.values():
                if cp["status"] == HITLStatus.PENDING:
                    if donor_id is None or cp["donor_id"] == donor_id:
                        pending.append(copy.deepcopy(cp))
            return pending


hitl_manager = HITLCheckpoint()
