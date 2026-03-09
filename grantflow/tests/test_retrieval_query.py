from __future__ import annotations

from grantflow.swarm.retrieval_query import (
    build_stage_query_text,
    donor_query_preset_terms,
    sanitize_revision_hint_for_query,
)


def test_donor_query_preset_terms_are_donor_aware():
    wb_terms = donor_query_preset_terms("worldbank")
    eu_terms = donor_query_preset_terms("eu")
    assert "project development objective" in wb_terms.lower()
    assert "results chain" in wb_terms.lower()
    assert "intermediate results indicators" in wb_terms.lower()
    assert "intervention logic" in eu_terms.lower()
    assert "specific objectives" in eu_terms.lower()
    assert "means of verification" in eu_terms.lower()


def test_build_stage_query_text_includes_context_hints_and_toc_clues():
    state = {
        "donor_id": "worldbank",
        "input_context": {
            "project": "Public Service Reform",
            "country": "Uzbekistan",
            "sector": "governance",
            "theme": "service_delivery",
        },
    }
    query = build_stage_query_text(
        state=state,
        stage="architect",
        project="Public Service Reform",
        country="Uzbekistan",
        revision_hint="Strengthen measurability",
        toc_payload={"project_development_objective": "Improve service delivery outcomes"},
    )
    lowered = query.lower()
    assert "architect" in lowered
    assert "public service reform" in lowered
    assert "uzbekistan" in lowered
    assert "strengthen measurability" in lowered
    assert "project development objective" in lowered
    assert "sector: governance" in lowered
    assert "theme: service_delivery" in lowered


def test_build_stage_query_text_can_skip_revision_hint_for_retrieval_queries():
    state = {
        "donor_id": "usaid",
        "input_context": {
            "project": "Civil Service AI",
            "country": "Kazakhstan",
            "sector": "governance",
        },
    }
    query = build_stage_query_text(
        state=state,
        stage="architect",
        project="Civil Service AI",
        country="Kazakhstan",
        revision_hint="Address the following issues before finalizing the draft: Replace repeated boilerplate. Grounding gate warning: architect_retrieval_no_hits.",
        toc_payload={"project_goal": "Improve responsible AI adoption in the civil service"},
        include_revision_hint=False,
    )
    lowered = query.lower()
    assert "civil service ai" in lowered
    assert "kazakhstan" in lowered
    assert "improve responsible ai adoption in the civil service" in lowered
    assert "replace repeated boilerplate" not in lowered
    assert "architect_retrieval_no_hits" not in lowered


def test_sanitize_revision_hint_for_query_drops_noisy_critic_prose():
    raw = """
    Address the following issues before finalizing the draft:
    Replace repeated boilerplate with section-specific causal logic.
    Grounding gate warning: architect_retrieval_no_hits.
    Strengthen measurability for outcome indicators.
    """
    sanitized = sanitize_revision_hint_for_query(raw)
    lowered = sanitized.lower()
    assert "address the following issues" not in lowered
    assert "architect_retrieval_no_hits" not in lowered
    assert "replace repeated boilerplate" not in lowered
    assert "strengthen measurability" in lowered


def test_build_stage_query_text_includes_eu_and_worldbank_toc_specific_hints():
    eu_query = build_stage_query_text(
        state={"donor_id": "eu", "input_context": {"project": "Digital Governance", "country": "Moldova"}},
        stage="architect",
        project="Digital Governance",
        country="Moldova",
        toc_payload={
            "overall_objective": {
                "title": "Improve digital governance performance",
                "rationale": "Improve service accountability",
            },
            "specific_objectives": [{"title": "Strengthen institutional capacity"}],
            "expected_outcomes": [{"expected_change": "Institutions demonstrate measurable improvements"}],
        },
    )
    wb_query = build_stage_query_text(
        state={
            "donor_id": "worldbank",
            "input_context": {"project": "Public Sector Performance", "country": "Uzbekistan"},
        },
        stage="architect",
        project="Public Sector Performance",
        country="Uzbekistan",
        toc_payload={
            "project_development_objective": "Improve service delivery performance",
            "objectives": [{"title": "Strengthen institutional performance"}],
            "results_chain": [{"description": "Agencies implement workflow improvements"}],
        },
    )

    eu_lower = eu_query.lower()
    wb_lower = wb_query.lower()
    assert "improve digital governance performance" in eu_lower
    assert "strengthen institutional capacity" in eu_lower
    assert "institutions demonstrate measurable improvements" in eu_lower
    assert "improve service delivery performance" in wb_lower
    assert "strengthen institutional performance" in wb_lower
    assert "agencies implement workflow improvements" in wb_lower
