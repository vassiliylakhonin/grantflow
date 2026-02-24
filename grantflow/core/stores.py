from __future__ import annotations

import copy
import json
import os
import sqlite3
import threading
from enum import Enum
from typing import Any, Dict, Optional

from grantflow.core.strategies.factory import DonorFactory


RUNTIME_STATE_KEYS = {"strategy", "donor_strategy"}
DEFAULT_SQLITE_BUSY_TIMEOUT_MS = 5000


def _env(name: str, default: str) -> str:
    legacy = name.replace("GRANTFLOW_", "AIDGRAPH_", 1) if name.startswith("GRANTFLOW_") else name
    return os.getenv(name, os.getenv(legacy, default))


def default_sqlite_path() -> str:
    return _env("GRANTFLOW_SQLITE_PATH", "./grantflow_state.db")


def sqlite_busy_timeout_ms() -> int:
    raw = _env("GRANTFLOW_SQLITE_BUSY_TIMEOUT_MS", str(DEFAULT_SQLITE_BUSY_TIMEOUT_MS))
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_SQLITE_BUSY_TIMEOUT_MS
    return max(0, value)


def storage_mode(name: str, default: str = "inmem") -> str:
    return _env(name, default).strip().lower()


def sanitize_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): sanitize_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_jsonable(item) for item in value]
    return str(value)


def prepare_state_for_storage(state: Any) -> Any:
    if not isinstance(state, dict):
        return sanitize_jsonable(state)

    stored_state: Dict[str, Any] = {}
    for key, value in state.items():
        if key in RUNTIME_STATE_KEYS:
            continue
        stored_state[str(key)] = sanitize_jsonable(value)
    return stored_state


def restore_state_from_storage(state: Any) -> Any:
    if not isinstance(state, dict):
        return state

    restored = copy.deepcopy(state)
    donor_id = restored.get("donor") or restored.get("donor_id")
    if donor_id and "donor_strategy" not in restored and "strategy" not in restored:
        try:
            strategy = DonorFactory.get_strategy(str(donor_id))
        except Exception:
            return restored
        restored["donor_strategy"] = strategy
        restored["strategy"] = strategy
    return restored


def prepare_job_payload_for_storage(payload: Dict[str, Any]) -> Dict[str, Any]:
    stored: Dict[str, Any] = {}
    for key, value in payload.items():
        if key == "state":
            stored[str(key)] = prepare_state_for_storage(value)
        else:
            stored[str(key)] = sanitize_jsonable(value)
    return stored


def restore_job_payload_from_storage(payload: Dict[str, Any]) -> Dict[str, Any]:
    restored = copy.deepcopy(payload)
    if "state" in restored:
        restored["state"] = restore_state_from_storage(restored["state"])
    return restored


def storage_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def storage_json_loads(value: str) -> Any:
    return json.loads(value)


def open_sqlite_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {sqlite_busy_timeout_ms()}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def ensure_sqlite_schema_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
          component TEXT PRIMARY KEY,
          version INTEGER NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def ensure_sqlite_component_schema(conn: sqlite3.Connection, component: str, target_version: int) -> int:
    ensure_sqlite_schema_meta(conn)
    row = conn.execute("SELECT version FROM schema_meta WHERE component = ?", (component,)).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO schema_meta (component, version, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (component, target_version),
        )
        return target_version

    current_version = int(row["version"])
    if current_version > target_version:
        raise RuntimeError(
            f"Unsupported newer schema for component '{component}': {current_version} > {target_version}"
        )
    if current_version < target_version:
        # Placeholder for future migrations; current schema is single-step and idempotent.
        conn.execute(
            """
            UPDATE schema_meta
            SET version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE component = ?
            """,
            (target_version, component),
        )
    return target_version


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set(self, job_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job_id] = copy.deepcopy(payload)

    def update(self, job_id: str, **patch: Any) -> Dict[str, Any]:
        with self._lock:
            current = copy.deepcopy(self._jobs.get(job_id, {}))
            current.update(patch)
            self._jobs[job_id] = copy.deepcopy(current)
            return copy.deepcopy(current)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            payload = self._jobs.get(job_id)
            return copy.deepcopy(payload) if payload is not None else None

    def list(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {job_id: copy.deepcopy(payload) for job_id, payload in self._jobs.items()}


class SQLiteJobStore:
    SCHEMA_COMPONENT = "jobs"
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or default_sqlite_path()
        self._write_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return open_sqlite_connection(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            ensure_sqlite_component_schema(conn, self.SCHEMA_COMPONENT, self.SCHEMA_VERSION)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                  job_id TEXT PRIMARY KEY,
                  payload_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def set(self, job_id: str, payload: Dict[str, Any]) -> None:
        stored_payload = prepare_job_payload_for_storage(payload)
        payload_json = storage_json_dumps(stored_payload)
        with self._write_lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO jobs (job_id, payload_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(job_id) DO UPDATE SET
                      payload_json=excluded.payload_json,
                      updated_at=CURRENT_TIMESTAMP
                    """,
                    (job_id, payload_json),
                )

    def update(self, job_id: str, **patch: Any) -> Dict[str, Any]:
        with self._write_lock:
            with self._connect() as conn:
                row = conn.execute("SELECT payload_json FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                current: Dict[str, Any] = storage_json_loads(row["payload_json"]) if row else {}
                merged = dict(current)
                merged.update(prepare_job_payload_for_storage(patch))
                conn.execute(
                    """
                    INSERT INTO jobs (job_id, payload_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(job_id) DO UPDATE SET
                      payload_json=excluded.payload_json,
                      updated_at=CURRENT_TIMESTAMP
                    """,
                    (job_id, storage_json_dumps(merged)),
                )
        return restore_job_payload_from_storage(merged)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        payload = storage_json_loads(row["payload_json"])
        return restore_job_payload_from_storage(payload)

    def list(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT job_id, payload_json FROM jobs ORDER BY updated_at DESC").fetchall()
        items: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            items[str(row["job_id"])] = restore_job_payload_from_storage(storage_json_loads(row["payload_json"]))
        return items


def create_job_store_from_env() -> InMemoryJobStore | SQLiteJobStore:
    mode = storage_mode("GRANTFLOW_JOB_STORE", _env("JOB_STORE", "inmem"))
    if mode == "sqlite":
        return SQLiteJobStore()
    return InMemoryJobStore()
