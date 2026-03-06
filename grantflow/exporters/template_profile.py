from __future__ import annotations

from typing import Any, Dict

from grantflow.exporters.toc_normalization import normalize_toc_for_export, unwrap_toc_payload

DONOR_TEMPLATE_ALIASES: dict[str, str] = {
    "usaid": "usaid",
    "eu": "eu",
    "worldbank": "worldbank",
    "giz": "giz",
    "un_agencies": "un_agencies",
    "undp": "un_agencies",
    "unicef": "un_agencies",
    "unhcr": "un_agencies",
    "wfp": "un_agencies",
    "unwomen": "un_agencies",
    "unfpa": "un_agencies",
    "state_department": "state_department",
    "us_state_department": "state_department",
    "u.s. department of state": "state_department",
    "us department of state": "state_department",
}

TEMPLATE_DISPLAY_NAMES: dict[str, str] = {
    "usaid": "USAID Results Framework",
    "eu": "EU Intervention Logic",
    "worldbank": "World Bank Results Framework",
    "giz": "GIZ Results & Sustainability Logic",
    "un_agencies": "UN Agency Program Logic",
    "state_department": "U.S. Department of State Program Logic",
    "generic": "Generic Proposal Template",
}

TEMPLATE_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "usaid": ["project_goal", "development_objectives"],
    "eu": ["overall_objective", "specific_objectives", "expected_outcomes"],
    "worldbank": ["project_development_objective", "objectives", "results_chain"],
    "giz": ["programme_objective", "outcomes"],
    "un_agencies": ["brief", "objectives"],
    "state_department": ["program_goal", "objectives"],
}


def normalize_export_template_key(donor_id: str) -> str:
    donor_key = str(donor_id or "").strip().lower()
    if not donor_key:
        return "generic"
    return DONOR_TEMPLATE_ALIASES.get(donor_key, "generic")


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def build_export_template_profile(*, donor_id: str, toc_payload: Dict[str, Any]) -> Dict[str, Any]:
    template_key = normalize_export_template_key(donor_id)
    normalized_toc_payload = normalize_toc_for_export(template_key, unwrap_toc_payload(toc_payload))
    required_sections = list(TEMPLATE_REQUIRED_SECTIONS.get(template_key, []))
    present_sections = [name for name in required_sections if _is_non_empty((normalized_toc_payload or {}).get(name))]
    missing_sections = [name for name in required_sections if name not in present_sections]
    coverage_rate = round(len(present_sections) / len(required_sections), 4) if required_sections else 1.0

    return {
        "donor_id": str(donor_id or ""),
        "template_key": template_key,
        "template_display_name": TEMPLATE_DISPLAY_NAMES.get(template_key, TEMPLATE_DISPLAY_NAMES["generic"]),
        "required_sections": required_sections,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "coverage_rate": coverage_rate,
    }
