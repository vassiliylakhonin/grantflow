from __future__ import annotations

from copy import deepcopy
from typing import Any

_DEMO_INGEST_PRESETS: dict[str, dict[str, Any]] = {
    "usaid_gov_ai_kazakhstan": {
        "donor_id": "usaid",
        "title": "AI civil service (KZ)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "governance",
            "theme": "responsible_ai_public_sector",
            "country_focus": "Kazakhstan",
            "doc_family": "donor_policy",
        },
        "checklist_items": [
            {"id": "donor_policy", "label": "USAID donor policy / ADS guidance", "source_type": "donor_guidance"},
            {
                "id": "responsible_ai_guidance",
                "label": "Responsible AI / digital governance guidance",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Kazakhstan public administration / digital government context",
                "source_type": "country_context",
            },
            {
                "id": "competency_framework",
                "label": "Civil service competency / training framework",
                "source_type": "training_framework",
            },
        ],
        "recommended_docs": [
            "USAID ADS / policy guidance relevant to digital transformation, governance, or capacity strengthening",
            "Responsible AI / digital governance guidance approved for your organization",
            "Kazakhstan public administration or digital government policy/context documents",
            "Civil service training standards / competency frameworks (if available)",
        ],
    },
    "eu_digital_governance_moldova": {
        "donor_id": "eu",
        "title": "Digital governance (MD)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "governance",
            "theme": "digital_service_delivery",
            "country_focus": "Moldova",
            "doc_family": "donor_results_guidance",
        },
        "checklist_items": [
            {
                "id": "donor_results_guidance",
                "label": "EU intervention logic / results framework guidance",
                "source_type": "donor_guidance",
            },
            {
                "id": "digital_governance_guidance",
                "label": "EU digital governance / service delivery references",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Moldova digitization policy / service standards",
                "source_type": "country_context",
            },
            {
                "id": "municipal_process_guidance",
                "label": "Municipal service process / quality guidance",
                "source_type": "implementation_reference",
            },
        ],
        "recommended_docs": [
            "EU intervention logic / results framework guidance relevant to governance and public administration reform",
            "EU digital governance or service delivery reform policy references",
            "Moldova public service digitization strategies / standards",
            "Municipal service quality standards or process management guidance",
        ],
    },
    "worldbank_public_sector_uzbekistan": {
        "donor_id": "worldbank",
        "title": "Public sector performance (UZ)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "public_sector_reform",
            "theme": "performance_management_service_delivery",
            "country_focus": "Uzbekistan",
            "doc_family": "donor_results_guidance",
        },
        "checklist_items": [
            {"id": "donor_results_guidance", "label": "World Bank RF / M&E guidance", "source_type": "donor_guidance"},
            {
                "id": "project_reference_docs",
                "label": "World Bank public sector modernization project references",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Uzbekistan public administration reform context",
                "source_type": "country_context",
            },
            {
                "id": "agency_process_docs",
                "label": "Agency service standards / process maps",
                "source_type": "implementation_reference",
            },
        ],
        "recommended_docs": [
            "World Bank results framework / M&E guidance relevant to governance or public sector reform",
            "World Bank public sector modernization / service delivery project documents",
            "Uzbekistan public administration reform strategies / performance frameworks",
            "Agency service standards, process maps, or reform guidance used for pilots",
        ],
    },
}


def list_ingest_preset_summaries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset_key in sorted(_DEMO_INGEST_PRESETS.keys()):
        preset = _DEMO_INGEST_PRESETS[preset_key]
        rows.append(
            {
                "preset_key": preset_key,
                "donor_id": str(preset.get("donor_id") or "").strip().lower() or None,
                "title": str(preset.get("title") or "").strip() or None,
            }
        )
    return rows


def load_ingest_preset(preset_key: str) -> dict[str, Any]:
    token = str(preset_key or "").strip()
    if not token:
        raise ValueError("Missing preset_key")
    if token not in _DEMO_INGEST_PRESETS:
        known = ", ".join(sorted(_DEMO_INGEST_PRESETS.keys()))
        raise ValueError(f"Unknown preset_key '{token}'. Available: {known}")
    payload = deepcopy(_DEMO_INGEST_PRESETS[token])
    payload["preset_key"] = token
    return payload

