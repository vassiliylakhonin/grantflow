from __future__ import annotations

import pytest

from grantflow.api.demo_presets import list_ingest_preset_summaries, load_ingest_preset


def test_list_ingest_preset_summaries_contains_expected_keys():
    rows = list_ingest_preset_summaries()
    assert isinstance(rows, list) and rows
    keys = {str(item.get("preset_key") or "") for item in rows if isinstance(item, dict)}
    assert "usaid_gov_ai_kazakhstan" in keys
    assert "eu_digital_governance_moldova" in keys
    assert "worldbank_public_sector_uzbekistan" in keys


def test_load_ingest_preset_returns_expected_structure():
    payload = load_ingest_preset("eu_digital_governance_moldova")
    assert payload["preset_key"] == "eu_digital_governance_moldova"
    assert payload["donor_id"] == "eu"
    assert isinstance(payload.get("metadata"), dict)
    assert isinstance(payload.get("checklist_items"), list)
    assert isinstance(payload.get("recommended_docs"), list)


def test_load_ingest_preset_raises_for_unknown_key():
    with pytest.raises(ValueError, match="Unknown preset_key"):
        load_ingest_preset("missing-preset")
