from __future__ import annotations

from grantflow.swarm.retrieval_query import build_stage_query_text, donor_query_preset_terms


def test_donor_query_preset_terms_are_donor_aware():
    wb_terms = donor_query_preset_terms("worldbank")
    eu_terms = donor_query_preset_terms("eu")
    assert "project development objective" in wb_terms.lower()
    assert "results chain" in wb_terms.lower()
    assert "intervention logic" in eu_terms.lower()
    assert "specific objectives" in eu_terms.lower()


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
