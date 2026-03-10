from __future__ import annotations

from copy import deepcopy
from typing import Any

_DEMO_GENERATE_PRESETS_LEGACY: dict[str, dict[str, Any]] = {
    "usaid_gov_ai_kazakhstan": {
        "donor_id": "usaid",
        "title": "AI civil service (KZ)",
        "generate_payload": {
            "donor_id": "usaid",
            "input_context": {
                "project": "Responsible AI Skills for Civil Service Modernization",
                "country": "Kazakhstan",
                "region": "National with pilot cohorts in Astana and Almaty",
                "timeframe": "2026-2027 (24 months)",
                "problem": (
                    "Civil servants have uneven practical skills in safe, ethical, and effective AI use for "
                    "public administration."
                ),
                "target_population": (
                    "Mid-level and senior civil servants in policy, service delivery, and digital transformation units."
                ),
                "expected_change": (
                    "Agencies improve AI readiness, adopt governance guidance, and demonstrate early workflow "
                    "efficiency gains."
                ),
                "key_activities": [
                    "Needs assessment and baseline competency mapping",
                    "Responsible AI curriculum design for public administration",
                    "Cohort-based training and training-of-trainers",
                    "Applied labs for policy and service workflows",
                    "SOP and governance guidance drafting support",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
    "eu_digital_governance_moldova": {
        "donor_id": "eu",
        "title": "Digital governance (MD)",
        "generate_payload": {
            "donor_id": "eu",
            "input_context": {
                "project": "Digital Governance Service Quality and Administrative Capacity",
                "country": "Moldova",
                "region": "National and selected municipalities",
                "timeframe": "2026-2028 (30 months)",
                "problem": "Public institutions face uneven digital service management capacity and inconsistent service quality.",
                "target_population": (
                    "Civil servants and municipal service managers in digital transformation and service delivery units."
                ),
                "expected_change": "Institutions adopt stronger service quality procedures and improve processing efficiency.",
                "key_activities": [
                    "Institutional workflow assessments",
                    "Training on service design and process improvement",
                    "Coaching for agency and municipal teams",
                    "Support for SOPs and service quality dashboards",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
    "worldbank_public_sector_uzbekistan": {
        "donor_id": "worldbank",
        "title": "Public sector performance (UZ)",
        "generate_payload": {
            "donor_id": "worldbank",
            "input_context": {
                "project": "Public Sector Performance and Service Delivery Capacity Strengthening",
                "country": "Uzbekistan",
                "region": "National ministries and selected subnational administrations",
                "timeframe": "2026-2028 (36 months)",
                "problem": (
                    "Public agencies have uneven capabilities in performance management and evidence-based decision-making."
                ),
                "target_population": "Government managers and civil servants in reform, performance, and service delivery functions.",
                "expected_change": (
                    "Participating institutions adopt stronger performance management practices and improve selected services."
                ),
                "key_activities": [
                    "Institutional diagnostics and process mapping",
                    "Capacity development for performance management and data use",
                    "Technical assistance for service improvement plans",
                    "Process optimization pilots and adaptive reviews",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
    "giz_sme_resilience_ukraine": {
        "donor_id": "giz",
        "title": "SME resilience (UA)",
        "generate_payload": {
            "donor_id": "giz",
            "input_context": {
                "project": "SME Resilience and Local Jobs",
                "country": "Ukraine",
                "region": "Selected municipalities and SME support ecosystems",
                "timeframe": "2026-2028 (30 months)",
                "problem": (
                    "Small and medium enterprises face disrupted operations, weak continuity planning, "
                    "and uneven access to practical resilience support."
                ),
                "target_population": (
                    "SMEs, local business support providers, and municipal economic development partners."
                ),
                "expected_change": (
                    "Participating SMEs adopt stronger resilience practices, stabilize operations, and retain jobs."
                ),
                "key_activities": [
                    "SME resilience diagnostics and prioritization",
                    "Business continuity coaching and peer learning",
                    "Support for local partner implementation routines",
                    "Resilience action plans and follow-up implementation reviews",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
    "state_department_media_georgia": {
        "donor_id": "state_department",
        "title": "Media resilience (GE)",
        "generate_payload": {
            "donor_id": "state_department",
            "input_context": {
                "project": "Independent Media Resilience",
                "country": "Georgia",
                "region": "National and selected local media ecosystems",
                "timeframe": "2026-2028 (24 months)",
                "problem": (
                    "Independent media organizations face political pressure, information-space threats, "
                    "and uneven capacity to manage operational and safeguarding risks."
                ),
                "target_population": (
                    "Independent media outlets, editors, journalists, and partner civil society support organizations."
                ),
                "expected_change": (
                    "Media partners improve resilience practices, protect editorial operations, and respond more "
                    "consistently to information integrity risks."
                ),
                "key_activities": [
                    "Partner risk and resilience assessments",
                    "Editorial and organizational resilience coaching",
                    "Safeguarding and contingency planning support",
                    "Peer exchange and monitoring of information integrity responses",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
    "un_agencies_education_nepal": {
        "donor_id": "un_agencies",
        "title": "Education recovery (NP)",
        "generate_payload": {
            "donor_id": "un_agencies",
            "input_context": {
                "project": "Inclusive Education Recovery",
                "country": "Nepal",
                "region": "Selected provinces and vulnerable school communities",
                "timeframe": "2026-2028 (24 months)",
                "problem": (
                    "Learners in crisis-affected communities face uneven access to inclusive education recovery "
                    "support and inconsistent service delivery across local institutions."
                ),
                "target_population": (
                    "Children, teachers, school leaders, and partner education institutions in vulnerable communities."
                ),
                "expected_change": (
                    "Partner institutions deliver more reliable inclusive education recovery support and improve "
                    "continuity for affected learners."
                ),
                "key_activities": [
                    "Partner education needs assessments",
                    "Teacher and school support packages",
                    "Inclusive education recovery planning with local institutions",
                    "Field monitoring and partner verification reviews",
                ],
            },
            "llm_mode": True,
            "hitl_enabled": True,
            "architect_rag_enabled": True,
            "strict_preflight": False,
        },
    },
}

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
    "giz_sme_resilience_ukraine": {
        "donor_id": "giz",
        "title": "SME resilience (UA)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "private_sector_development",
            "theme": "sme_resilience_and_jobs",
            "country_focus": "Ukraine",
            "doc_family": "donor_results_guidance",
        },
        "checklist_items": [
            {
                "id": "donor_results_guidance",
                "label": "GIZ results and sustainability guidance",
                "source_type": "donor_guidance",
            },
            {
                "id": "sme_resilience_guidance",
                "label": "SME resilience / continuity support references",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Ukraine SME recovery / economic resilience context",
                "source_type": "country_context",
            },
            {
                "id": "partner_delivery_docs",
                "label": "Partner implementation and review references",
                "source_type": "implementation_reference",
            },
        ],
        "recommended_docs": [
            "GIZ programme guidance on results, implementation, and sustainability",
            "SME resilience or business continuity support references used by implementing partners",
            "Ukraine SME recovery or local jobs context references",
            "Partner implementation review templates or delivery monitoring notes",
        ],
    },
    "state_department_media_georgia": {
        "donor_id": "state_department",
        "title": "Media resilience (GE)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "media_and_information_integrity",
            "theme": "independent_media_resilience",
            "country_focus": "Georgia",
            "doc_family": "donor_results_guidance",
        },
        "checklist_items": [
            {
                "id": "donor_results_guidance",
                "label": "State Department program logic / DRG guidance",
                "source_type": "donor_guidance",
            },
            {
                "id": "media_resilience_guidance",
                "label": "Media resilience / information integrity references",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Georgia media environment / civic space context",
                "source_type": "country_context",
            },
            {
                "id": "partner_risk_docs",
                "label": "Partner safeguarding / contingency planning references",
                "source_type": "implementation_reference",
            },
        ],
        "recommended_docs": [
            "State Department DRG / public affairs guidance relevant to media resilience",
            "Information integrity or independent media support references",
            "Georgia media environment / civic space context references",
            "Partner safeguarding, contingency planning, or risk review templates",
        ],
    },
    "un_agencies_education_nepal": {
        "donor_id": "un_agencies",
        "title": "Education recovery (NP)",
        "metadata": {
            "source_type": "donor_guidance",
            "sector": "education",
            "theme": "inclusive_education_recovery",
            "country_focus": "Nepal",
            "doc_family": "donor_results_guidance",
        },
        "checklist_items": [
            {
                "id": "donor_results_guidance",
                "label": "UN results framework / reporting guidance",
                "source_type": "donor_guidance",
            },
            {
                "id": "education_recovery_guidance",
                "label": "Inclusive education recovery references",
                "source_type": "reference_guidance",
            },
            {
                "id": "country_context",
                "label": "Nepal education recovery / access context",
                "source_type": "country_context",
            },
            {
                "id": "partner_verification_docs",
                "label": "Partner monitoring / field verification references",
                "source_type": "implementation_reference",
            },
        ],
        "recommended_docs": [
            "UN results framework / reporting guidance relevant to education recovery",
            "Inclusive education recovery references used by implementing partners",
            "Nepal education access or recovery context references",
            "Partner monitoring, field verification, or sector-review templates",
        ],
    },
}


def list_generate_legacy_preset_summaries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for preset_key in sorted(_DEMO_GENERATE_PRESETS_LEGACY.keys()):
        preset = _DEMO_GENERATE_PRESETS_LEGACY[preset_key]
        rows.append(
            {
                "preset_key": preset_key,
                "donor_id": str(preset.get("donor_id") or "").strip().lower() or None,
                "title": str(preset.get("title") or "").strip() or None,
            }
        )
    return rows


def load_generate_legacy_preset(preset_key: str) -> dict[str, Any]:
    token = str(preset_key or "").strip()
    if not token:
        raise ValueError("Missing preset_key")
    if token not in _DEMO_GENERATE_PRESETS_LEGACY:
        known = ", ".join(sorted(_DEMO_GENERATE_PRESETS_LEGACY.keys()))
        raise ValueError(f"Unknown preset_key '{token}'. Available: {known}")
    payload = deepcopy(_DEMO_GENERATE_PRESETS_LEGACY[token])
    payload["preset_key"] = token
    return payload


def list_generate_legacy_preset_details() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list_generate_legacy_preset_summaries():
        key = str(item.get("preset_key") or "").strip()
        if not key:
            continue
        rows.append(load_generate_legacy_preset(key))
    return rows


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


def list_ingest_preset_details() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list_ingest_preset_summaries():
        key = str(item.get("preset_key") or "").strip()
        if not key:
            continue
        rows.append(load_ingest_preset(key))
    return rows
