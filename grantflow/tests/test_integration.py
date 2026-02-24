# grantflow/tests/test_integration.py

import time
from fastapi.testclient import TestClient

from grantflow.api.app import app

client = TestClient(app)


def _wait_for_terminal_status(job_id: str, timeout_s: float = 3.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        response = client.get(f"/status/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"done", "error", "pending_hitl"}:
            return body
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for job completion")


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_donors():
    response = client.get("/donors")
    assert response.status_code == 200
    donors = response.json()["donors"]
    donor_ids = [d["id"] for d in donors]
    assert "usaid" in donor_ids
    assert "eu" in donor_ids
    assert "worldbank" in donor_ids


def test_generate_basic_async_job_flow():
    payload = {
        "donor_id": "usaid",
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": False,
        "hitl_enabled": False,
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data

    status = _wait_for_terminal_status(data["job_id"])
    assert status["status"] == "done"
    state = status["state"]
    assert state["toc_draft"]
    assert state["logframe_draft"]
    assert state["quality_score"] >= 0


def test_status_redacts_internal_strategy_objects():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Governance Support", "country": "Ukraine"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    assert "donor_strategy" not in state
    assert "strategy" not in state
    assert state["donor_id"] == "usaid"
    assert state["toc_draft"]


def test_hitl_pause_resume_flow():
    response = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Education", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": True,
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "pending_hitl"
    assert status["checkpoint_stage"] == "toc"

    cp_id = status["checkpoint_id"]
    approve = client.post(
        "/hitl/approve",
        json={"checkpoint_id": cp_id, "approved": True, "feedback": "TOC approved"},
    )
    assert approve.status_code == 200

    resume = client.post(f"/resume/{job_id}", json={})
    assert resume.status_code == 200
    assert resume.json()["resuming_from"] == "mel"

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "pending_hitl"
    assert status["checkpoint_stage"] == "logframe"

    cp_id = status["checkpoint_id"]
    approve = client.post(
        "/hitl/approve",
        json={"checkpoint_id": cp_id, "approved": True, "feedback": "Logframe approved"},
    )
    assert approve.status_code == 200

    resume = client.post(f"/resume/{job_id}", json={})
    assert resume.status_code == 200
    assert resume.json()["resuming_from"] == "critic"

    status = _wait_for_terminal_status(job_id)
    assert status["status"] == "done"
    state = status["state"]
    assert state["toc_draft"]
    assert state["logframe_draft"]
    assert (state.get("critic_notes") or {}).get("engine") in {"fallback", None} or str((state.get("critic_notes") or {}).get("engine", "")).startswith("llm:")


def test_generate_rejects_old_contract_shape():
    response = client.post(
        "/generate",
        json={"donor": "usaid", "input": {"project": "Water"}},
    )
    assert response.status_code == 422


def test_export_both_zip():
    gen = client.post(
        "/generate",
        json={
            "donor_id": "usaid",
            "input_context": {"project": "Health", "country": "Kenya"},
            "llm_mode": False,
            "hitl_enabled": False,
        },
    )
    job_id = gen.json()["job_id"]
    status = _wait_for_terminal_status(job_id)
    state = status["state"]

    export = client.post("/export", json={"payload": state, "format": "both"})
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/zip")
    assert b"PK" == export.content[:2]


def test_hitl_checkpoint_endpoints():
    from grantflow.swarm.hitl import hitl_manager

    checkpoint_id = hitl_manager.create_checkpoint(
        stage="toc",
        state={"test": "data"},
        donor_id="USAID",
    )

    response = client.get("/hitl/pending")
    assert response.status_code == 200
    assert response.json()["pending_count"] >= 1
    checkpoints = response.json()["checkpoints"]
    matching = [cp for cp in checkpoints if cp["id"] == checkpoint_id]
    assert matching
    assert "state_snapshot" not in matching[0]
    assert matching[0]["has_state_snapshot"] is True

    response = client.post(
        "/hitl/approve",
        json={
            "checkpoint_id": checkpoint_id,
            "approved": True,
            "feedback": "Looks good",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
