import json
import sqlite3

from grantflow.core.stores import SQLiteIngestAuditStore, SQLiteJobStore, open_sqlite_connection
from grantflow.core.strategies.factory import DonorFactory
from grantflow.swarm.hitl import HITLCheckpoint, HITLStatus


def test_sqlite_job_store_persists_json_and_rehydrates_strategy(tmp_path):
    db_path = tmp_path / "grantflow_state.db"
    store = SQLiteJobStore(str(db_path))
    strategy = DonorFactory.get_strategy("usaid")

    store.set(
        "job-1",
        {
            "status": "accepted",
            "hitl_enabled": False,
            "state": {
                "donor_id": "usaid",
                "donor": "usaid",
                "strategy": strategy,
                "donor_strategy": strategy,
                "input_context": {"project": "Health"},
            },
        },
    )

    restored = store.get("job-1")
    assert restored is not None
    assert restored["status"] == "accepted"
    assert restored["state"]["donor_id"] == "usaid"
    assert restored["state"]["strategy"].get_rag_collection() == "usaid_ads201"
    assert restored["state"]["donor_strategy"].get_rag_collection() == "usaid_ads201"

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT payload_json FROM jobs WHERE job_id = ?", ("job-1",)).fetchone()
    raw_payload = json.loads(row[0])
    assert "strategy" not in raw_payload["state"]
    assert "donor_strategy" not in raw_payload["state"]


def test_sqlite_job_store_update_merges_and_restores(tmp_path):
    db_path = tmp_path / "grantflow_state.db"
    store = SQLiteJobStore(str(db_path))
    store.set("job-2", {"status": "accepted", "state": {"donor_id": "eu"}})

    updated = store.update("job-2", status="running", state={"donor_id": "eu", "progress": 50})
    assert updated["status"] == "running"
    assert updated["state"]["progress"] == 50
    assert updated["state"]["strategy"].get_rag_collection() == "eu_intpa"


def test_sqlite_job_store_list_returns_all_jobs(tmp_path):
    db_path = tmp_path / "grantflow_state.db"
    store = SQLiteJobStore(str(db_path))
    store.set("job-a", {"status": "accepted", "state": {"donor_id": "usaid"}})
    store.set("job-b", {"status": "done", "state": {"donor_id": "eu"}})

    items = store.list()
    assert set(items.keys()) == {"job-a", "job-b"}
    assert items["job-a"]["state"]["strategy"].get_rag_collection() == "usaid_ads201"
    assert items["job-b"]["state"]["strategy"].get_rag_collection() == "eu_intpa"


def test_sqlite_hitl_checkpoint_store_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("GRANTFLOW_HITL_STORE", "sqlite")
    monkeypatch.setenv("GRANTFLOW_SQLITE_PATH", str(tmp_path / "grantflow_state.db"))

    manager = HITLCheckpoint()
    strategy = DonorFactory.get_strategy("usaid")
    checkpoint_id = manager.create_checkpoint(
        stage="toc",
        state={"donor_id": "usaid", "strategy": strategy, "foo": "bar"},
        donor_id="usaid",
    )

    checkpoint = manager.get_checkpoint(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["status"] == HITLStatus.PENDING
    assert checkpoint["stage"] == "toc"
    assert checkpoint["state_snapshot"]["foo"] == "bar"
    assert "strategy" not in checkpoint["state_snapshot"]

    pending = manager.list_pending()
    assert any(cp["id"] == checkpoint_id for cp in pending)

    assert manager.approve(checkpoint_id, "ok")
    assert manager.is_approved(checkpoint_id) is True

    checkpoint = manager.get_checkpoint(checkpoint_id)
    assert checkpoint is not None
    assert checkpoint["status"] == HITLStatus.APPROVED
    assert checkpoint["feedback"] == "ok"


def test_sqlite_ingest_audit_store_roundtrip_and_filtering(tmp_path):
    db_path = tmp_path / "grantflow_state.db"
    store = SQLiteIngestAuditStore(str(db_path))

    store.append(
        {
            "event_id": "evt-1",
            "ts": "2026-02-25T10:00:00+00:00",
            "donor_id": "usaid",
            "namespace": "usaid_ads201",
            "filename": "ads.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "donor_policy"},
            "result": {"chunks_ingested": 3},
        }
    )
    store.append(
        {
            "event_id": "evt-2",
            "ts": "2026-02-25T10:05:00+00:00",
            "donor_id": "eu",
            "namespace": "eu_intpa",
            "filename": "eu.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "donor_policy"},
            "result": {"chunks_ingested": 2},
        }
    )
    store.append(
        {
            "event_id": "evt-3",
            "ts": "2026-02-25T10:10:00+00:00",
            "donor_id": "usaid",
            "namespace": "usaid_ads201",
            "filename": "kz-context.pdf",
            "content_type": "application/pdf",
            "metadata": {"doc_family": "country_context"},
            "result": {"chunks_ingested": 4},
        }
    )

    usaid_rows = store.list_recent(donor_id="usaid", limit=10)
    assert [row["filename"] for row in usaid_rows] == ["kz-context.pdf", "ads.pdf"]
    assert usaid_rows[0]["metadata"]["doc_family"] == "country_context"
    assert usaid_rows[1]["result"]["chunks_ingested"] == 3

    all_rows = store.list_recent(limit=2)
    assert len(all_rows) == 2
    assert [row["event_id"] for row in all_rows] == ["evt-3", "evt-2"]


def test_sqlite_stores_initialize_pragmas_and_schema_meta(monkeypatch, tmp_path):
    db_path = tmp_path / "grantflow_state.db"
    monkeypatch.setenv("GRANTFLOW_SQLITE_PATH", str(db_path))
    monkeypatch.setenv("GRANTFLOW_HITL_STORE", "sqlite")
    monkeypatch.setenv("GRANTFLOW_INGEST_STORE", "sqlite")
    monkeypatch.setenv("GRANTFLOW_SQLITE_BUSY_TIMEOUT_MS", "7000")

    SQLiteJobStore(str(db_path))
    HITLCheckpoint()
    SQLiteIngestAuditStore(str(db_path))

    with open_sqlite_connection(str(db_path)) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        rows = conn.execute("SELECT component, version FROM schema_meta ORDER BY component").fetchall()
        rows = [(row["component"], row["version"]) for row in rows]

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 7000
    assert ("hitl_checkpoints", 1) in rows
    assert ("ingest_audit", 1) in rows
    assert ("jobs", 1) in rows


def test_sqlite_job_store_upgrades_schema_meta_version_on_reinit(tmp_path):
    db_path = tmp_path / "grantflow_state.db"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
              component TEXT PRIMARY KEY,
              version INTEGER NOT NULL,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_meta (component, version) VALUES (?, ?)",
            ("jobs", 0),
        )

    SQLiteJobStore(str(db_path))

    with sqlite3.connect(str(db_path)) as conn:
        version = conn.execute(
            "SELECT version FROM schema_meta WHERE component = ?",
            ("jobs",),
        ).fetchone()[0]

    assert int(version) == 1
