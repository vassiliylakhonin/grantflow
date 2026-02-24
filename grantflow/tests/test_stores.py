import json
import sqlite3

from grantflow.core.stores import SQLiteJobStore
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
