from __future__ import annotations

import json
from pathlib import Path

from grantflow.api.public_views import public_job_payload
from grantflow.core.strategies.catalog import resolve_donor_record
from grantflow.memory_bank.vector_store import VectorStore
from grantflow.swarm.citations import append_citations
from grantflow.swarm.versioning import append_draft_version


def test_donor_resolution_contract_for_key_aliases():
    golden_cases = [
        {"query": "USAID", "id": "usaid", "strategy": "usaid", "rag_namespace": "usaid_ads201"},
        {"query": "usaid.gov", "id": "usaid", "strategy": "usaid", "rag_namespace": "usaid_ads201"},
        {"query": "european-union", "id": "eu", "strategy": "eu", "rag_namespace": "eu_intpa"},
        {
            "query": "world_bank",
            "id": "worldbank",
            "strategy": "worldbank",
            "rag_namespace": "worldbank_ads301",
        },
        {
            "query": "state_department",
            "id": "us_state_department",
            "strategy": "state_department",
            "rag_namespace": "us_state_department_guidance",
        },
        {
            "query": "undp",
            "id": "un_agencies",
            "strategy": "generic",
            "rag_namespace": "un_agencies_guidance",
        },
    ]

    for case in golden_cases:
        resolved = resolve_donor_record(case["query"])
        assert resolved is not None
        assert resolved["id"] == case["id"]
        assert resolved["strategy"] == case["strategy"]
        assert resolved["rag_namespace"] == case["rag_namespace"]


def test_vector_store_memory_fallback_contract():
    store = VectorStore()
    store.client = None

    namespace = "Tenant A / USAID ADS 201"
    store.upsert(
        namespace=namespace,
        ids=["doc-1", "doc-2"],
        documents=["Water and sanitation implementation guidance", "Macroeconomic outlook brief"],
        metadatas=[{"source": "guidance.pdf", "chunk_id": "c1"}, {"source": "context.pdf", "chunk_id": "c2"}],
    )

    queried = store.query(namespace=namespace, query_texts="sanitation guidance", top_k=1)
    assert isinstance(queried, list)
    assert queried
    assert "guidance" in queried[0].lower()

    stats = store.get_stats(namespace)
    assert stats["backend"] == "memory"
    assert stats["document_count"] == 2
    assert stats["collection"].startswith("grantflow_tenant_a_usaid_ads_201")


def test_append_citations_deduplicates_and_preserves_traceability():
    state = {}
    incoming = [
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "namespace": "usaid_ads201",
            "source": "ads.pdf",
            "page": 12,
            "chunk": 1,
            "chunk_id": "usaid_ads201_p12_c1",
            "used_for": "toc.project_goal",
            "statement_path": "toc.project_goal",
            "label": "USAID ADS 201 p.12",
        },
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "namespace": "usaid_ads201",
            "source": "ads.pdf",
            "page": 12,
            "chunk": 1,
            "chunk_id": "usaid_ads201_p12_c1",
            "used_for": "toc.project_goal",
            "statement_path": "toc.project_goal",
            "label": "USAID ADS 201 p.12",
        },
    ]
    append_citations(state, incoming)
    assert len(state["citations"]) == 1
    assert state["citations"][0]["chunk_id"] == "usaid_ads201_p12_c1"


def test_append_draft_version_skips_duplicate_consecutive_payloads():
    state = {}
    toc_payload = {"toc": {"brief": "v1"}}
    append_draft_version(state, section="toc", content=toc_payload, node="architect", iteration=1)
    append_draft_version(state, section="toc", content=toc_payload, node="architect", iteration=1)
    append_draft_version(state, section="toc", content={"toc": {"brief": "v2"}}, node="architect", iteration=2)

    versions = state["draft_versions"]
    assert len(versions) == 2
    assert versions[0]["version_id"] == "toc_v1"
    assert versions[1]["version_id"] == "toc_v2"
    assert versions[0]["sequence"] == 1
    assert versions[1]["sequence"] == 2


def test_public_job_payload_matches_golden_snapshot():
    fixture_path = Path(__file__).parent / "fixtures" / "public_job_payload_golden.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    job = {
        "status": "done",
        "hitl_enabled": False,
        "webhook_url": "https://example.com/hook",
        "webhook_secret": "secret",
        "job_events": [{"event_id": "e1"}],
        "review_comments": [{"comment_id": "c1"}],
        "client_metadata": {"source": "demo"},
        "state": {
            "donor_id": "usaid",
            "strategy": {"internal": "secret"},
            "donor_strategy": {"internal": "secret"},
            "toc_draft": {"toc": {"brief": "Sample"}},
        },
    }

    actual = public_job_payload(job)
    assert actual == expected
