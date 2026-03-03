from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grantflow.api.public_views import (
    public_job_critic_payload,
    public_job_export_payload,
    public_job_payload,
    public_job_quality_payload,
)
from grantflow.core.strategies.catalog import resolve_donor_record
from grantflow.memory_bank.vector_store import VectorStore
from grantflow.swarm.citations import append_citations
from grantflow.swarm.versioning import append_draft_version

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_json(name: str) -> Any:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _sample_quality_contract_job() -> dict[str, Any]:
    return {
        "status": "done",
        "hitl_enabled": True,
        "strict_preflight": True,
        "generate_preflight": {
            "donor_id": "usaid",
            "coverage_rate": 0.5,
            "risk_level": "medium",
            "warning_count": 1,
            "warnings": [{"code": "LOW_DOC_COVERAGE", "severity": "medium", "message": "Coverage low"}],
        },
        "client_metadata": {
            "donor_id": "usaid",
            "demo_generate_preset_key": "usaid_gov_ai_kazakhstan",
            "rag_readiness": {
                "donor_id": "usaid",
                "expected_doc_families": ["donor_policy", "country_context", "responsible_ai_guidance"],
            },
        },
        "review_comments": [
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "author": "reviewer",
                "message": "Need stronger evidence for outcome chain",
                "linked_finding_id": "finding-1",
                "version_id": "toc_v1",
                "ts": "2026-03-01T10:03:00+00:00",
            }
        ],
        "job_events": [
            {"event_id": "e1", "type": "status_changed", "to_status": "accepted", "ts": "2026-03-01T10:00:00+00:00"},
            {"event_id": "e2", "type": "status_changed", "to_status": "running", "ts": "2026-03-01T10:00:05+00:00"},
            {
                "event_id": "e3",
                "type": "status_changed",
                "to_status": "pending_hitl",
                "ts": "2026-03-01T10:01:00+00:00",
            },
            {"event_id": "e4", "type": "resume_requested", "ts": "2026-03-01T10:02:00+00:00"},
            {"event_id": "e5", "type": "status_changed", "to_status": "running", "ts": "2026-03-01T10:02:10+00:00"},
            {"event_id": "e6", "type": "status_changed", "to_status": "done", "ts": "2026-03-01T10:04:00+00:00"},
        ],
        "state": {
            "donor_id": "usaid",
            "quality_score": 7.2,
            "critic_score": 6.8,
            "needs_revision": True,
            "toc_validation": {"valid": True, "schema_name": "USAIDToCSchema"},
            "toc_generation_meta": {
                "engine": "llm:gpt-4.1-mini",
                "llm_used": True,
                "retrieval_used": True,
                "citation_policy": {"threshold_mode": "donor_section"},
            },
            "architect_retrieval": {
                "enabled": True,
                "hits_count": 2,
                "namespace": "tenant_a/usaid_ads201",
            },
            "mel_generation_meta": {
                "engine": "deterministic:retrieval_template",
                "llm_used": False,
                "retrieval_used": True,
            },
            "logframe_draft": {
                "rag_trace": {
                    "namespace": "tenant_a/usaid_ads201",
                    "used_results": 2,
                    "avg_retrieval_confidence": 0.64,
                }
            },
            "mel_grounding_policy": {
                "mode": "warn",
                "blocking": False,
                "reason": "mel_grounding_signals_ok",
            },
            "citations": [
                {
                    "stage": "architect",
                    "citation_type": "rag_claim_support",
                    "citation_confidence": 0.82,
                    "confidence_threshold": 0.5,
                    "traceability_status": "complete",
                    "used_for": "toc_claim",
                },
                {
                    "stage": "architect",
                    "citation_type": "rag_low_confidence",
                    "citation_confidence": 0.25,
                    "confidence_threshold": 0.5,
                    "traceability_status": "partial",
                    "used_for": "toc_claim",
                },
                {
                    "stage": "mel",
                    "citation_type": "fallback_namespace",
                    "citation_confidence": 0.1,
                    "traceability_status": "missing",
                    "used_for": "IND_001",
                },
            ],
            "critic_notes": {
                "engine": "rules+llm:gpt-4.1-mini",
                "rule_score": 7.0,
                "llm_score": 6.5,
                "revision_instructions": "Fix TOC evidence gaps and tighten MEL indicators.",
                "fatal_flaws": [
                    {
                        "id": "finding-1",
                        "finding_id": "finding-1",
                        "status": "open",
                        "severity": "high",
                        "section": "toc",
                        "code": "TOC_EVIDENCE_GAP",
                        "message": "Outcome chain lacks grounded support.",
                        "source": "rules",
                        "version_id": "toc_v1",
                    },
                    {
                        "id": "finding-2",
                        "finding_id": "finding-2",
                        "status": "acknowledged",
                        "severity": "medium",
                        "section": "logframe",
                        "code": "MEL_BASELINE_WEAK",
                        "message": "Baselines are not explicit.",
                        "source": "llm",
                        "label": "BASELINE_TARGET_MISSING",
                        "version_id": "logframe_v1",
                    },
                ],
                "rule_checks": [
                    {"check": "toc_schema_valid", "status": "pass"},
                    {"check": "evidence_grounding", "status": "fail"},
                    {"check": "mel_alignment", "status": "warn"},
                ],
                "llm_advisory_diagnostics": {
                    "applied": False,
                    "reason": "architect_fallback_citations_present",
                },
                "llm_advisory_normalization": {
                    "applied": True,
                    "downgraded_count": 1,
                },
                "llm_advisory_score_calibration": {
                    "applied": True,
                    "max_llm_penalty": 0.75,
                },
            },
        },
    }


def test_donor_resolution_contract_for_key_aliases():
    fixture = _fixture_json("donor_resolution_golden.json")
    golden_cases = fixture.get("cases") if isinstance(fixture, dict) else None
    assert isinstance(golden_cases, list) and golden_cases

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
    assert state["citations"][0]["doc_id"] == "usaid_ads201_p12_c1"
    assert state["citations"][0]["chunk_id"] == "usaid_ads201_p12_c1"


def test_append_citations_prefers_higher_quality_duplicate():
    state = {}
    append_citations(
        state,
        [
            {
                "stage": "architect",
                "citation_type": "rag_low_confidence",
                "namespace": "usaid_ads201",
                "source": "ads.pdf",
                "page": 12,
                "chunk_id": "usaid_ads201_p12_c1",
                "used_for": "toc.project_goal",
                "statement_path": "toc.project_goal",
                "label": "USAID ADS 201 p.12",
                "citation_confidence": 0.2,
                "retrieval_confidence": 0.25,
                "retrieval_rank": 4,
            },
            {
                "stage": "architect",
                "citation_type": "rag_low_confidence",
                "namespace": "usaid_ads201",
                "source": "ads.pdf",
                "page": 12,
                "chunk_id": "usaid_ads201_p12_c1",
                "used_for": "toc.project_goal",
                "statement_path": "toc.project_goal",
                "label": "USAID ADS 201 p.12",
                "citation_confidence": 0.72,
                "retrieval_confidence": 0.82,
                "retrieval_rank": 1,
            },
        ],
    )
    assert len(state["citations"]) == 1
    row = state["citations"][0]
    assert row["citation_confidence"] == 0.72
    assert row["retrieval_confidence"] == 0.82
    assert row["retrieval_rank"] == 1


def test_citations_and_versioning_match_golden_snapshot():
    fixture = _fixture_json("citations_versioning_golden.json")
    incoming = fixture.get("incoming_citations") if isinstance(fixture, dict) else None
    expected = fixture.get("expected") if isinstance(fixture, dict) else None
    assert isinstance(incoming, list) and isinstance(expected, dict)

    state: dict[str, Any] = {}
    append_citations(state, incoming)
    append_draft_version(state, section="toc", content={"toc": {"brief": "v1"}}, node="architect", iteration=1)
    append_draft_version(state, section="toc", content={"toc": {"brief": "v1"}}, node="architect", iteration=1)
    append_draft_version(state, section="toc", content={"toc": {"brief": "v2"}}, node="architect", iteration=2)

    actual = {
        "citations": state.get("citations") or [],
        "draft_versions": [
            {
                "version_id": row.get("version_id"),
                "sequence": row.get("sequence"),
                "section": row.get("section"),
                "node": row.get("node"),
                "iteration": row.get("iteration"),
            }
            for row in (state.get("draft_versions") or [])
            if isinstance(row, dict)
        ],
    }
    assert actual == expected


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
    expected = _fixture_json("public_job_payload_golden.json")

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


def test_public_job_export_payload_matches_golden_snapshot_and_redacts_strategy():
    expected = _fixture_json("public_job_export_payload_golden.json")
    job = {
        "status": "done",
        "webhook_url": "https://example.com/hook",
        "webhook_secret": "secret",
        "state": {
            "donor_id": "usaid",
            "strategy": {"internal": "x"},
            "donor_strategy": {"internal": "y"},
            "toc_draft": {"toc": {"brief": "Sample"}},
            "critic_notes": {
                "fatal_flaws": [
                    {
                        "finding_id": "finding-1",
                        "status": "open",
                        "severity": "high",
                        "section": "toc",
                        "code": "TOC_GAP",
                        "message": "Missing output chain",
                        "source": "rules",
                    }
                ]
            },
        },
        "review_comments": [
            {
                "comment_id": "comment-1",
                "status": "open",
                "section": "toc",
                "author": "rev",
                "message": "Need details",
                "linked_finding_id": "finding-1",
                "version_id": "toc_v1",
                "ts": "2026-02-27T00:00:00Z",
            }
        ],
    }

    actual = public_job_export_payload("job-1", job)
    assert actual == expected
    state = ((actual.get("payload") or {}).get("state") or {}) if isinstance(actual, dict) else {}
    assert "strategy" not in state
    assert "donor_strategy" not in state


def test_public_job_critic_payload_matches_golden_snapshot():
    expected = _fixture_json("public_job_critic_payload_golden.json")
    job = _sample_quality_contract_job()
    actual = public_job_critic_payload("job-quality-1", job)
    assert actual == expected


def test_public_job_quality_payload_matches_golden_snapshot():
    expected = _fixture_json("public_job_quality_payload_golden.json")
    job = _sample_quality_contract_job()
    inventory_rows = [
        {"doc_family": "donor_policy", "count": 2},
        {"doc_family": "country_context", "count": 0},
        {"doc_family": "responsible_ai_guidance", "count": 1},
    ]
    actual = public_job_quality_payload("job-quality-1", job, ingest_inventory_rows=inventory_rows)
    assert actual == expected
