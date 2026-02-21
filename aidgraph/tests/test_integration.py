# aidgraph/tests/test_integration.py

import pytest
from fastapi.testclient import TestClient
from aidgraph.api.app import app

client = TestClient(app)

def test_health_endpoint():
    """Проверяет health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_donors():
    """Проверяет список доноров."""
    response = client.get("/donors")
    assert response.status_code == 200
    donors = response.json()["donors"]
    assert len(donors) >= 3
    donor_ids = [d["id"] for d in donors]
    assert "usaid" in donor_ids
    assert "eu" in donor_ids
    assert "worldbank" in donor_ids

def test_generate_basic():
    """Проверяет базовую генерацию."""
    payload = {
        "donor_id": "USAID",
        "input_context": {"project": "Water Sanitation", "country": "Kenya"},
        "llm_mode": True,
        "hitl_enabled": False
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

def test_hitl_flow():
    """Проверяет HITL flow."""
    # Создаём checkpoint
    from aidgraph.swarm.hitl import hitl_manager
    checkpoint_id = hitl_manager.create_checkpoint(
        stage="toc",
        state={"test": "data"},
        donor_id="USAID"
    )
    
    # Проверяем список pending
    response = client.get("/hitl/pending")
    assert response.status_code == 200
    assert response.json()["pending_count"] >= 1
    
    # Одобряем
    response = client.post("/hitl/approve", json={
        "checkpoint_id": checkpoint_id,
        "approved": True,
        "feedback": "Looks good"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
