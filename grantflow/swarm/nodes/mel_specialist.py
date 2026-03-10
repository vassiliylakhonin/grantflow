# grantflow/swarm/nodes/mel_specialist.py

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citation_source import citation_label_from_metadata, citation_source_from_metadata
from grantflow.swarm.citations import append_citations, citation_traceability_status
from grantflow.swarm.llm_provider import (
    chat_openai_init_kwargs,
    llm_model_candidates,
    openai_compatible_llm_available,
    openai_compatible_missing_reason,
)
from grantflow.swarm.retrieval_query import build_stage_query_text
from grantflow.swarm.state_contract import (
    normalize_state_contract,
    state_donor_id,
    state_donor_strategy,
    state_input_context,
    state_iteration,
    state_llm_mode,
    state_rag_namespace,
    state_revision_hint,
)
from grantflow.swarm.versioning import append_draft_version

MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD = 0.35
MEL_MAX_EVIDENCE_PROMPT_HITS = 3
MEL_CITATION_DONOR_THRESHOLD_OVERRIDES: dict[str, float] = {
    "usaid": 0.33,
    "worldbank": 0.32,
    "eu": 0.32,
    "giz": 0.3,
    "state_department": 0.3,
    "us_state_department": 0.3,
}
MEL_PLACEHOLDER_BASELINE_TARGET_VALUES = {
    "",
    "tbd",
    "to be determined",
    "placeholder",
    "n/a",
    "na",
    "unknown",
    "-",
    "--",
    "none",
    "null",
}


class MELIndicatorOutput(BaseModel):
    indicator_id: str = Field(description="Indicator identifier")
    name: str = Field(description="Indicator title")
    justification: str = Field(description="Why this indicator is relevant for the ToC")
    citation: str = Field(description="Citation label/reference string")
    baseline: str = Field(default="TBD", description="Current baseline")
    target: str = Field(default="TBD", description="Target value")
    evidence_excerpt: Optional[str] = Field(default=None, description="Grounding excerpt summary")


class MELDraftOutput(BaseModel):
    indicators: list[MELIndicatorOutput] = Field(default_factory=list)


def _model_validate(schema_cls: type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    validator = getattr(schema_cls, "model_validate", None)
    if callable(validator):
        return validator(payload)
    return schema_cls.parse_obj(payload)


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    dumper = getattr(model, "model_dump", None)
    if callable(dumper):
        return dumper()
    return model.dict()


def _safe_json(value: Any, *, max_chars: int = 1600) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        text = str(value)
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."


def _is_basemodel_subclass(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    if origin is not Union:
        return annotation
    args = [a for a in get_args(annotation) if a is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


def _type_label(annotation: Any) -> str:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        inner = _type_label(args[0]) if args else "Any"
        return f"list[{inner}]"
    if origin is dict:
        return "object"
    if _is_basemodel_subclass(annotation):
        return str(getattr(annotation, "__name__", "object"))
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


def _field_description(field: Any) -> str:
    description = getattr(field, "description", None)
    if isinstance(description, str) and description.strip():
        return description.strip()
    field_info = getattr(field, "field_info", None)
    if field_info is not None:
        desc = getattr(field_info, "description", None)
        if isinstance(desc, str) and desc.strip():
            return desc.strip()
    return ""


def _field_required(field: Any) -> bool:
    is_required_fn = getattr(field, "is_required", None)
    if callable(is_required_fn):
        try:
            return bool(is_required_fn())
        except Exception:
            pass
    required = getattr(field, "required", None)
    if isinstance(required, bool):
        return required
    return False


def _schema_contract_hint(schema_cls: Type[BaseModel], *, max_fields: int = 24) -> str:
    fields = getattr(schema_cls, "model_fields", None)
    if not isinstance(fields, dict):  # pydantic v1 fallback
        fields = getattr(schema_cls, "__fields__", {})
    if not isinstance(fields, dict) or not fields:
        return ""

    lines: list[str] = []
    for field_name, field in list(fields.items())[:max_fields]:
        annotation = getattr(field, "annotation", None) or getattr(field, "outer_type_", None) or str
        required = "required" if _field_required(field) else "optional"
        description = _field_description(field)
        line = f"- {field_name}: {_type_label(annotation)} ({required})"
        if description:
            line += f" - {description}"
        lines.append(line)
    return "\n".join(lines)


def _resolve_mel_schema_cls(strategy: Any) -> Type[BaseModel]:
    getter = getattr(strategy, "get_mel_schema", None)
    if callable(getter):
        try:
            candidate = getter()
        except Exception:
            candidate = None
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return candidate
    return MELDraftOutput


def _extract_mel_indicators(payload: Dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        return []
    for key in ("indicators", "mel_indicators", "logframe_indicators"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _mel_statement_priority(path: str) -> int:
    lowered = str(path or "").lower()
    if any(token in lowered for token in (".project_goal", ".program_goal", ".programme_objective")):
        return 5
    if any(
        token in lowered
        for token in (
            ".development_objectives[",
            ".specific_objectives[",
            ".objectives[",
            ".project_development_objective",
        )
    ):
        return 4
    if any(token in lowered for token in (".expected_outcomes[", ".results_chain[", ".outcomes[", ".outputs[")):
        return 3
    if any(token in lowered for token in ("goal", "objective", "outcome", "result", "output", "change")):
        return 2
    return 1


def _extract_toc_result_statements(value: Any, path: str = "toc") -> list[tuple[str, str, int]]:
    statements: list[tuple[str, str, int]] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            statements.extend(_extract_toc_result_statements(inner, f"{path}.{key}"))
        return statements
    if isinstance(value, list):
        for idx, inner in enumerate(value):
            statements.extend(_extract_toc_result_statements(inner, f"{path}[{idx}]"))
        return statements
    if not isinstance(value, str):
        return statements

    text = " ".join(value.split()).strip()
    if not text:
        return statements
    lowered_path = path.lower()
    skip_tokens = (
        "_id",
        ".id",
        "indicator_code",
        ".citation",
        ".code",
        ".assumption",
        ".assumptions",
        ".risk",
        ".risks",
        ".stakeholder",
        ".context",
    )
    if any(token in lowered_path for token in skip_tokens):
        return statements
    if len(text) < 12:
        return statements

    statements.append((path, text, _mel_statement_priority(path)))
    return statements


def _dedupe_toc_result_statements(items: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, int]] = []
    for path, statement, priority in sorted(
        items,
        key=lambda row: (-int(row[2]), len(str(row[0])), str(row[0])),
    ):
        key = (str(path).strip().lower(), str(statement).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append((path, statement, priority))
    return out


def _compact_indicator_label(text: str, *, max_len: int = 88) -> str:
    compact = " ".join(str(text or "").split()).strip(" .;:-")
    if not compact:
        return ""
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 3].rstrip()}..."


def _statement_to_indicator_phrase(statement: str) -> str:
    compact = " ".join(str(statement or "").split()).strip().rstrip(".")
    if not compact:
        return ""
    compact = re.sub(r"\bevidence\s+hint\s*:?\s*[^.]+\.?", "", compact, flags=re.IGNORECASE).strip(" .;:-")
    compact = re.sub(
        r"\bintervention delivers measurable change\b",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(r"\bresults delivered\b", "", compact, flags=re.IGNORECASE).strip(" ,;:-")
    compact = re.sub(r"\boutcomes?\s+(in|for|across)\b", r"\1", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\bresults?\s+(in|for|across)\b", r"\1", compact, flags=re.IGNORECASE)
    compact = re.sub(
        r"\bthrough structured implementation and review cycles\b",
        "",
        compact,
        flags=re.IGNORECASE,
    ).strip(" ,;:-")
    compact = re.sub(r"\beviden[a-z]*\b.*$", "", compact, flags=re.IGNORECASE).strip(" .;:-")
    compact = re.sub(r"\s+\.", ".", compact)
    normalized = re.sub(r"^[\"'`]+|[\"'`]+$", "", compact)
    replacements = (
        (r"^improve\s+", "Improved "),
        (r"^strengthen\s+", "Strengthened "),
        (r"^increase\s+", "Increased "),
        (r"^expand\s+", "Expanded "),
        (r"^enhance\s+", "Enhanced "),
        (r"^reduce\s+", "Reduced "),
        (r"^develop\s+", "Developed "),
        (r"^build\s+", "Built "),
        (r"^support\s+", "Supported "),
        (r"^enable\s+", "Enabled "),
    )
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        if updated != normalized:
            normalized = updated
            break
    return normalized[:1].upper() + normalized[1:] if normalized else ""


def _statement_focus_phrase(statement: str) -> str:
    text = " ".join(str(statement or "").split()).strip().rstrip(".")
    if not text:
        return "priority result"
    lowered_text = text.lower()
    phrase_overrides = (
        ("digital governance performance", "digital governance performance"),
        ("digital governance service delivery", "digital governance service delivery"),
        ("public sector performance and service delivery", "public sector performance & service delivery"),
        ("public sector performance", "public sector performance"),
        ("service delivery", "service delivery"),
        ("institutional capacity", "institutional capacity"),
        ("inclusive education recovery", "inclusive education recovery"),
        ("youth employment", "youth employment"),
        ("independent media resilience", "independent media resilience"),
        ("information integrity", "information integrity"),
        ("civic accountability", "civic accountability"),
    )
    for phrase, replacement in phrase_overrides:
        if phrase in lowered_text:
            return replacement
    text = re.sub(r"\bevidence\s+hint\s*:?\s*[^.]+\.?", "", text, flags=re.IGNORECASE).strip(" .;:-")
    text = re.sub(
        r"\bintervention delivers measurable change\b",
        "results delivery",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bthrough structured implementation and review cycles\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ,;:-")
    text = re.sub(r"\beviden[a-z]*\b.*$", "", text, flags=re.IGNORECASE).strip(" .;:-")
    text = re.sub(r"\s+\.", ".", text)
    normalized = re.sub(r"^[\"'`]+|[\"'`]+$", "", text)
    normalized = re.sub(
        r"^(improve|strengthen|increase|expand|enhance|reduce|develop|build|support|enable|promote)\s+",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\b(in|for|across|among|through|via|with|within|under|on)\b.*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip(" ,;:-")
    if not normalized:
        normalized = text
    return _compact_indicator_label(normalized.lower(), max_len=52)


def _indicator_name_from_toc_statement(statement: str, *, idx: int, result_level: str = "") -> str:
    phrase = _statement_to_indicator_phrase(statement)
    if not phrase:
        return f"Results indicator {idx + 1}"
    level = _normalize_result_level(result_level)
    prefix = {
        "impact": "Impact",
        "outcome": "Outcome",
        "output": "Output",
    }.get(level, "Result")
    return _compact_indicator_label(f"{prefix}: {phrase}")


def _infer_result_level_from_toc_path(path: str) -> str:
    lowered = str(path or "").strip().lower()
    if any(token in lowered for token in (".project_goal", ".program_goal", ".programme_objective")):
        return "impact"
    if any(
        token in lowered
        for token in (
            ".development_objectives[",
            ".specific_objectives[",
            ".objectives[",
            ".project_development_objective",
        )
    ):
        return "outcome"
    if any(token in lowered for token in (".results_chain[", ".expected_outcomes[", ".outcomes[")):
        return "outcome"
    if ".outputs[" in lowered:
        return "output"
    return "outcome"


def _normalize_result_level(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"impact", "outcome", "output"}:
        return token
    if token in {"results", "result", "intermediate_result", "objective"}:
        return "outcome"
    if token in {"deliverable", "activity"}:
        return "output"
    return ""


def _default_frequency_for_donor(donor_id: str, *, result_level: str) -> str:
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "outcome").strip().lower() or "outcome"
    base_by_level = {
        "output": "monthly",
        "outcome": "quarterly",
        "impact": "annual",
    }
    base = base_by_level.get(level, "quarterly")
    if donor == "usaid":
        return "quarterly" if level in {"output", "outcome"} else "annual"
    if donor == "eu":
        return "quarterly" if level == "output" else "semiannual"
    if donor == "worldbank":
        return "quarterly" if level == "output" else "annual"
    if donor in {"giz", "state_department", "us_state_department"}:
        return "quarterly"
    if donor == "un_agencies":
        return "quarterly" if level == "output" else "semiannual"
    return base


def _default_data_source_for_donor(donor_id: str, *, result_level: str, indicator_name: str = "") -> str:
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "outcome").strip().lower() or "outcome"
    name = str(indicator_name or "").strip().lower()
    default_sources = {
        "output": "Program monitoring records and implementer reports",
        "outcome": "Monitoring database and partner verification records",
        "impact": "Evaluation studies and administrative datasets",
    }
    if donor == "usaid":
        if any(token in name for token in ("service", "coverage", "adoption", "policy", "capacity", "governance")):
            sources = {
                "output": "IP activity records, training records, and partner performance reports",
                "outcome": "PMP tracking tables, partner performance reports, and verification spot-checks",
                "impact": "CLA evidence, evaluation studies, and validated administrative datasets",
            }
            return sources.get(level, sources["outcome"])
        sources = {
            "output": "IP performance monitoring records and partner reports",
            "outcome": "Performance monitoring plan (PMP) datasets and verification records",
            "impact": "Learning agenda studies and national administrative datasets",
        }
        return sources.get(level, sources["outcome"])
    if donor == "eu":
        if any(token in name for token in ("service", "coverage", "institutional", "adoption", "performance")):
            sources = {
                "output": "Action implementation trackers, partner reports, and verification files",
                "outcome": "Intervention logic tracking tables, means of verification annexes, and partner validation records",
                "impact": "External evaluations, official statistics, and programme review evidence",
            }
            return sources.get(level, sources["outcome"])
        sources = {
            "output": "Action logframe monitoring records and partner progress reports",
            "outcome": "Logframe outcome tracking datasets and verification missions",
            "impact": "External evaluations and national statistics",
        }
        return sources.get(level, sources["outcome"])
    if donor == "worldbank":
        if any(
            token in name for token in ("service", "performance", "adoption", "institutional capacity", "public sector")
        ):
            sources = {
                "output": "PIU implementation trackers, agency MIS extracts, and supervision aide-memoires",
                "outcome": "Results framework updates, ISR evidence, and agency verification records",
                "impact": "ICR evidence, administrative performance datasets, and sector review findings",
            }
            return sources.get(level, sources["outcome"])
        sources = {
            "output": "Project implementation support records and agency MIS",
            "outcome": "Results framework monitoring tables and ISR evidence",
            "impact": "Project completion evaluations and national administrative data",
        }
        return sources.get(level, sources["outcome"])
    if donor in {"giz", "state_department", "us_state_department"}:
        if donor in {"state_department", "us_state_department"} and any(
            token in name for token in ("media", "journalist", "newsroom", "civil society", "resilience")
        ):
            sources = {
                "output": "Partner activity records, newsroom support logs, and verification notes",
                "outcome": "Partner monitoring records, resilience reviews, and media support verification files",
                "impact": "Independent assessments, partner risk reviews, and sector monitoring datasets",
            }
            return sources.get(level, sources["outcome"])
        if donor in {"state_department", "us_state_department"} and _is_state_department_civic_indicator(name):
            sources = {
                "output": "Partner activity records, stakeholder engagement logs, and verification notes",
                "outcome": "Partner monitoring records, civic risk reviews, and stakeholder verification files",
                "impact": "Independent assessments, stakeholder perception reviews, and sector monitoring datasets",
            }
            return sources.get(level, sources["outcome"])
        sources = {
            "output": "Implementing partner monitoring records",
            "outcome": "Partner verification records and periodic outcome reviews",
            "impact": "Independent assessments and administrative datasets",
        }
        return sources.get(level, sources["outcome"])
    if donor == "un_agencies":
        if any(token in name for token in ("education", "school", "learning", "teacher", "student", "child")):
            sources = {
                "output": "Programme monitoring records, partner 5W trackers, and school-level activity reports",
                "outcome": "Partner verification records, education monitoring datasets, and field monitoring notes",
                "impact": "Sector assessments, official education statistics, and inter-agency review evidence",
            }
            return sources.get(level, sources["outcome"])
        sources = {
            "output": "Programme monitoring records, partner 5W trackers, and implementation reports",
            "outcome": "Partner verification records, field monitoring notes, and programme review datasets",
            "impact": "Inter-agency assessments, official statistics, and programme review evidence",
        }
        return sources.get(level, sources["outcome"])
    return default_sources.get(level, default_sources["outcome"])


def _default_indicator_definition_for_donor(indicator_name: str, *, donor_id: str, result_level: str) -> str:
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "outcome").strip().lower() or "outcome"
    label = str(indicator_name or "Indicator").strip() or "Indicator"
    name = label.lower()
    if donor == "usaid":
        if any(token in name for token in ("service", "coverage", "adoption", "policy", "capacity", "governance")):
            return (
                f"{label} measured at {level} level using USAID-style performance monitoring definitions, "
                "disaggregation expectations, and documented spot-check verification."
            )
        return (
            f"{label} measured at {level} level using USAID-style performance monitoring definitions and "
            "documented verification criteria."
        )
    if donor == "eu":
        if any(token in name for token in ("service", "coverage", "institutional", "adoption", "performance")):
            return (
                f"{label} measured at {level} level in the EU intervention logic with explicit means of verification, "
                "service-standard checks, partner validation, and delivery-performance review."
            )
        return (
            f"{label} measured at {level} level in the intervention logic with explicit means of verification, "
            "implementation review, and periodic partner validation."
        )
    if donor == "worldbank":
        if any(
            token in name for token in ("service", "performance", "adoption", "institutional capacity", "public sector")
        ):
            if level == "impact":
                return (
                    f"{label} measured at impact level as a Project Development Objective-style result using "
                    "verified government performance evidence and completion-stage review."
                )
            return (
                f"{label} measured at {level} level in a World Bank-style results framework using ISR-ready "
                "implementation evidence, agency verification, and PDO/intermediate-results review."
            )
        return (
            f"{label} measured at {level} level in the results framework using verified implementation evidence, "
            "results reporting, and ISR-style follow-up."
        )
    if donor == "giz":
        return (
            f"{label} measured at {level} level with partner delivery evidence, implementation validation, "
            "and sustainability-oriented review."
        )
    if donor in {"state_department", "us_state_department"}:
        if any(token in name for token in ("media", "journalist", "newsroom", "civil society", "resilience")):
            return (
                f"{label} measured at {level} level using independent-media resilience evidence, partner "
                "verification checks, and periodic risk review."
            )
        if _is_state_department_civic_indicator(name):
            return (
                f"{label} measured at {level} level using civic-actor monitoring evidence, partner verification "
                "checks, and periodic risk-context review."
            )
        return (
            f"{label} measured at {level} level using program management evidence, verification checks, and "
            "periodic risk review."
        )
    if donor == "un_agencies":
        if any(token in name for token in ("education", "school", "learning", "teacher", "student", "child")):
            return (
                f"{label} measured at {level} level as a UN programme result using partner verification, "
                "field monitoring, partner reporting, and sector-review evidence."
            )
        return (
            f"{label} measured at {level} level as a UN programme result using partner verification, "
            "field monitoring, partner reporting, and inter-agency review evidence."
        )
    return f"{label} tracked at {level} level."


def _default_indicator_formula(indicator_name: str, *, result_level: str, donor_id: str = "") -> str:
    name = str(indicator_name or "").strip().lower()
    level = str(result_level or "").strip().lower()
    donor = str(donor_id or "").strip().lower()
    if any(token in name for token in ("percent", "%", "rate", "coverage", "share")):
        return "(Numerator / Denominator) * 100"
    if any(token in name for token in ("time", "days", "duration", "turnaround", "delay", "processing")):
        return "Average days between service start and completion"
    if donor == "usaid" and any(
        token in name for token in ("official", "civil servant", "skills", "capacity", "training")
    ):
        return "Count of civil servants meeting verified completion or applied-skills criteria"
    if donor == "eu" and any(token in name for token in ("service quality", "institutional", "adoption", "procedure")):
        return "Count of institutions adopting verified service quality or administrative procedures"
    if donor == "worldbank" and any(token in name for token in ("performance", "public sector", "service delivery")):
        return "Count of institutions achieving verified service-performance improvements"
    if donor == "giz" and any(token in name for token in ("sme", "enterprise", "resilience", "business continuity")):
        return "Count of SMEs implementing verified resilience or continuity practices"
    if donor in {"state_department", "us_state_department"} and any(
        token in name for token in ("media", "newsroom", "journalist", "civil society", "resilience")
    ):
        return "Count of organizations implementing verified resilience or protection practices"
    if donor in {"state_department", "us_state_department"} and _is_state_department_civic_indicator(name):
        return "Count of organizations implementing verified civic or information-integrity practices"
    if donor == "un_agencies" and any(
        token in name for token in ("education", "school", "learning", "facility", "service access")
    ):
        return "Count of institutions/facilities meeting verified programme delivery criteria"
    if donor == "un_agencies" and any(token in name for token in ("child", "student", "teacher", "beneficiary")):
        return "Count of individuals meeting verified access or participation criteria"
    if _is_institution_indicator(name) or _is_organization_indicator(name):
        return "Count of institutions/organizations meeting defined performance or adoption criteria"
    if any(token in name for token in ("policy", "regulation", "protocol", "guideline", "sop")):
        return "Count of approved policies/protocols meeting quality criteria"
    if any(token in name for token in ("train", "certif", "capacity", "skills", "official", "staff")):
        return "Count of individuals meeting completion/certification criteria"
    if level == "impact":
        return "Change versus baseline at endline"
    return "Count of verified results achieved in reporting period"


def _deterministic_indicator_justification(
    *,
    donor_id: str,
    statement_path: str,
    result_level: str = "",
    statement: str = "",
) -> str:
    donor = str(donor_id or "").strip().lower()
    level = _normalize_result_level(result_level) or _infer_result_level_from_toc_path(statement_path)
    level_label = {
        "impact": "impact-level change",
        "outcome": "outcome-level change",
        "output": "delivery/result output",
    }.get(level, "causal result")
    statement_ref = _compact_indicator_label(_statement_to_indicator_phrase(statement), max_len=72) or statement_path
    focus = _statement_focus_phrase(statement)
    if donor == "eu":
        return (
            f"Maps {level_label} '{statement_ref}' from `{statement_path}` into an EU intervention-logic indicator "
            f"covering {focus} with monitoring, service-standard verification, and implementation-evidence intent."
        )
    if donor == "worldbank":
        return (
            f"Maps {level_label} '{statement_ref}' from `{statement_path}` into a World Bank-style results framework "
            f"indicator covering {focus} for verified implementation, ISR-style tracking, and results-framework review."
        )
    if donor in {"state_department", "us_state_department"}:
        return (
            f"Maps {level_label} '{statement_ref}' from `{statement_path}` into a State Department-style program "
            f"indicator covering {focus} for monitored delivery and resilience review."
        )
    if donor == "usaid":
        return (
            f"Maps {level_label} '{statement_ref}' from `{statement_path}` into a USAID-style performance indicator "
            f"covering {focus} and aligned with PMP-oriented monitoring, disaggregation, and verification logic."
        )
    if donor == "un_agencies":
        return (
            f"Maps {level_label} '{statement_ref}' from `{statement_path}` into a UN programme indicator "
            f"covering {focus} for field monitoring, partner verification, partner reporting, and sector-review use."
        )
    return (
        f"Deterministic MEL mapping for {level_label} '{statement_ref}' from `{statement_path}` covering {focus}. "
        "Tracks delivery of the causal results chain."
    )


def _deterministic_definition_from_statement(
    *,
    donor_id: str,
    result_level: str,
    statement: str,
    indicator_name: str,
) -> str:
    donor = str(donor_id or "").strip().lower()
    level = _normalize_result_level(result_level) or "outcome"
    focus = _statement_focus_phrase(statement)
    label = str(indicator_name or "Indicator").strip() or "Indicator"
    if donor == "usaid":
        return (
            f"{label} tracks {focus} as a {level}-level USAID performance result with PMP-oriented evidence, "
            "disaggregation expectations, and documented verification."
        )
    if donor == "eu":
        return (
            f"{label} tracks {focus} as a {level}-level EU intervention-logic result with explicit means of "
            "verification, partner validation, and service-delivery evidence review."
        )
    if donor == "worldbank":
        if level == "impact":
            return (
                f"{label} tracks {focus} as an impact-level Project Development Objective-style result using "
                "verified government performance evidence and completion-stage review."
            )
        return (
            f"{label} tracks {focus} as a {level}-level World Bank results framework result using ISR-ready "
            "implementation evidence, agency verification, and PDO/intermediate-results review."
        )
    if donor == "giz":
        return (
            f"{label} tracks {focus} as a {level}-level GIZ delivery result with partner evidence and "
            "sustainability-oriented review."
        )
    if donor in {"state_department", "us_state_department"}:
        return (
            f"{label} tracks {focus} as a {level}-level State Department program result using partner verification, "
            "delivery monitoring, and resilience-oriented review."
        )
    if donor == "un_agencies":
        return (
            f"{label} tracks {focus} as a {level}-level UN programme result using partner verification, "
            "field monitoring, partner reporting, and inter-agency review evidence."
        )
    return f"{label} tracks {focus} at {level} level."


def _is_generic_indicator_justification(text: str) -> bool:
    normalized = " ".join(str(text or "").split()).strip().lower()
    if not normalized:
        return True
    generic_tokens = (
        "indicator selected for mel coverage",
        "selected from donor-specific rag collection",
        "selected from rag collection",
        "selected based on project and toc relevance",
        "tracks completion performance",
        "tracks service performance",
        "tracks agency performance improvements",
        "tracks resilience adoption",
    )
    return any(token in normalized for token in generic_tokens)


def _retrieval_indicator_justification(
    *,
    donor_id: str,
    namespace: str,
    toc_statement_path: str,
    result_level: str,
    indicator_name: str,
) -> str:
    donor = str(donor_id or "").strip().lower()
    level = _normalize_result_level(result_level) or _infer_result_level_from_toc_path(toc_statement_path)
    level_label = {
        "impact": "impact-level result",
        "outcome": "outcome-level result",
        "output": "delivery/output result",
    }.get(level, "causal result")
    name_ref = _compact_indicator_label(indicator_name, max_len=72) or "indicator"
    if donor == "usaid":
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for PMP-oriented monitoring and verification."
        )
    if donor == "eu":
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for intervention-logic monitoring, service-standard checks, and means-of-verification review."
        )
    if donor == "worldbank":
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for results framework, implementation-status tracking, and PDO/intermediate-results review."
        )
    if donor == "giz":
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for delivery monitoring and sustainability-oriented review."
        )
    if donor in {"state_department", "us_state_department"}:
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for program delivery and resilience-focused review."
        )
    if donor == "un_agencies":
        return (
            f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
            "for UN programme monitoring, partner verification, partner reporting, and sector-review use."
        )
    return (
        f"Retrieved {name_ref} from `{namespace}` and aligned it to `{toc_statement_path}` as a {level_label} "
        "for MEL coverage."
    )


def _retrieval_evidence_signal(
    *,
    donor_id: str,
    excerpt: str,
    source: str,
    namespace: str,
) -> str:
    donor = str(donor_id or "").strip().lower()
    text = " ".join(f"{excerpt} {source} {namespace}".split()).lower()
    if donor == "usaid":
        if any(token in text for token in ("pmp", "performance management plan", "indicator reference sheet")):
            return "PMP and indicator reference evidence"
        if any(token in text for token in ("cla", "learning agenda", "site visit", "spot-check")):
            return "CLA and verification evidence"
        return "USAID monitoring package evidence"
    if donor == "eu":
        if any(token in text for token in ("annex", "means of verification", "verification mission")):
            return "verification annex evidence"
        if any(token in text for token in ("action document", "logframe", "intervention logic")):
            return "intervention-logic evidence"
        return "EU intervention evidence"
    if donor == "worldbank":
        if any(token in text for token in ("isr", "implementation status", "aide-memoire", "aide memoire")):
            return "ISR and aide-memoire evidence"
        if any(token in text for token in ("pdo", "results framework", "intermediate results")):
            return "results framework evidence"
        return "World Bank implementation evidence"
    if donor == "giz":
        if any(token in text for token in ("sustainability", "partner validation", "implementation review")):
            return "sustainability and partner validation evidence"
        return "GIZ delivery evidence"
    if donor in {"state_department", "us_state_department"}:
        if any(token in text for token in ("editorial risk", "resilience review", "media partner")):
            return "resilience review evidence"
        if any(token in text for token in ("verification", "risk log", "partner monitoring")):
            return "partner verification evidence"
        return "State Department program evidence"
    if donor == "un_agencies":
        if any(token in text for token in ("cluster", "inter-agency", "sector review")):
            return "inter-agency review evidence"
        if any(token in text for token in ("5w", "partner monitoring", "field monitoring", "verification")):
            return "partner and field monitoring evidence"
        return "UN programme evidence"
    return "retrieved donor evidence"


def _retrieval_definition_from_hit(
    *,
    donor_id: str,
    namespace: str,
    toc_statement_path: str,
    result_level: str,
    indicator_name: str,
    excerpt: str,
    source: str,
) -> str:
    donor = str(donor_id or "").strip().lower()
    level = _normalize_result_level(result_level) or _infer_result_level_from_toc_path(toc_statement_path)
    level_label = level or "outcome"
    signal = _retrieval_evidence_signal(
        donor_id=donor_id,
        excerpt=excerpt,
        source=source,
        namespace=namespace,
    )
    label = str(indicator_name or "Indicator").strip() or "Indicator"
    if donor == "usaid":
        return (
            f"{label} tracks a {level_label}-level USAID performance result using {signal}, "
            "aligned to PMP-style monitoring and documented verification."
        )
    if donor == "eu":
        return (
            f"{label} tracks a {level_label}-level EU intervention result using {signal}, "
            "explicit means of verification, service-standard checks, and partner validation logic."
        )
    if donor == "worldbank":
        if level == "impact":
            return (
                f"{label} tracks an impact-level Project Development Objective-style result using {signal}, "
                "with completion-stage review and agency verification intent."
            )
        return (
            f"{label} tracks a {level_label}-level World Bank results-framework result using {signal}, "
            "with implementation-status, agency verification, and results-framework review intent."
        )
    if donor == "giz":
        return (
            f"{label} tracks a {level_label}-level GIZ delivery result using {signal} "
            "and sustainability-oriented review."
        )
    if donor in {"state_department", "us_state_department"}:
        return (
            f"{label} tracks a {level_label}-level State Department program result using {signal} "
            "for delivery monitoring and resilience-oriented review."
        )
    if donor == "un_agencies":
        return (
            f"{label} tracks a {level_label}-level UN programme result using {signal} "
            "for partner verification, field monitoring, partner reporting, and sector-review use."
        )
    return f"{label} tracks a {level_label}-level result using {signal}."


def _default_disaggregation(indicator_name: str, *, donor_id: str, result_level: str) -> list[str]:
    name = str(indicator_name or "").strip().lower()
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "").strip().lower()
    base = ["location"]
    if donor == "eu" and level == "outcome":
        base = ["location", "partner_type"]
    elif donor == "worldbank" and level in {"outcome", "impact"}:
        base = ["location", "institution_type"]
    elif donor in {"state_department", "us_state_department"}:
        base = ["location", "participant_group"]
    elif donor == "un_agencies":
        base = ["sex", "age", "location"]
    if any(token in name for token in ("train", "official", "staff", "beneficiar", "participant", "people")):
        return ["sex", "age", "location"]
    if any(token in name for token in ("coverage", "rate", "service")):
        return ["location", "service_type"]
    return base


def _default_owner_for_donor(donor_id: str, *, result_level: str, indicator_name: str = "") -> str:
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "outcome").strip().lower() or "outcome"
    name = str(indicator_name or "").strip().lower()
    if donor == "usaid":
        if any(token in name for token in ("service", "coverage", "adoption", "policy", "capacity", "governance")):
            return "MEL lead, COR-aligned activity team, and implementing partner M&E focal points"
        return "MEL lead and implementing partner M&E team" if level != "impact" else "CLA/MEL lead"
    if donor == "eu":
        if any(token in name for token in ("service", "coverage", "institutional", "adoption", "performance")):
            return "Project M&E manager, partner focal points, and intervention logic lead"
        return "Project M&E manager and partner focal points"
    if donor == "worldbank":
        if any(
            token in name for token in ("service", "performance", "adoption", "institutional capacity", "public sector")
        ):
            return "PIU results lead and implementing agency performance focal points"
        return "PIU M&E specialist and implementing agency focal points"
    if donor == "giz":
        return "Programme M&E advisor, delivery partners, and sustainability focal points"
    if donor in {"state_department", "us_state_department"}:
        if any(token in name for token in ("media", "journalist", "newsroom", "civil society", "resilience")):
            return "Program manager, partner MEL focal point, and media partner leads"
        if _is_state_department_civic_indicator(name):
            return "Program manager, partner MEL focal point, and civic engagement leads"
        return "Program manager and partner MEL focal point"
    if donor == "un_agencies":
        return "Programme manager, partner M&E focal point, and sector coordination lead"
    return "MEL lead"


def _default_means_of_verification_for_donor(donor_id: str, *, result_level: str, indicator_name: str = "") -> str:
    donor = str(donor_id or "").strip().lower()
    level = str(result_level or "outcome").strip().lower() or "outcome"
    name = str(indicator_name or "").strip().lower()
    if donor == "usaid":
        if any(token in name for token in ("service", "coverage", "adoption", "policy", "capacity", "governance")):
            mapping = {
                "output": "Partner delivery records, attendance sheets, and implementation evidence files",
                "outcome": "PMP records, verification spot-checks, and partner evidence files",
                "impact": "Evaluation reports, CLA evidence, and validated administrative datasets",
            }
            return mapping.get(level, mapping["outcome"])
        mapping = {
            "output": "Partner delivery records, attendance sheets, and activity reports",
            "outcome": "Verified PMP datasets, spot checks, and partner evidence files",
            "impact": "Evaluation reports and validated administrative datasets",
        }
        return mapping.get(level, mapping["outcome"])
    if donor == "eu":
        if any(token in name for token in ("service", "coverage", "institutional", "adoption", "performance")):
            mapping = {
                "output": "Implementation trackers, partner reports, and verification files",
                "outcome": "Intervention logic tracking tables, means of verification annexes, and field validation notes",
                "impact": "External evaluations, official statistics, and programme review evidence",
            }
            return mapping.get(level, mapping["outcome"])
        mapping = {
            "output": "Logframe monitoring tables, partner reports, and verification files",
            "outcome": "Outcome tracking tables, means of verification annexes, and field validation notes",
            "impact": "External evaluations and official statistics",
        }
        return mapping.get(level, mapping["outcome"])
    if donor == "worldbank":
        if any(
            token in name for token in ("service", "performance", "adoption", "institutional capacity", "public sector")
        ):
            mapping = {
                "output": "Supervision mission records, PIU progress trackers, and agency MIS extracts",
                "outcome": "ISR aide-memoires, results framework updates, and agency verification records",
                "impact": "ICR evidence, administrative performance statistics, and validation notes",
            }
            return mapping.get(level, mapping["outcome"])
        mapping = {
            "output": "Implementation support records and agency management information systems",
            "outcome": "ISR evidence, results framework tables, and agency verification records",
            "impact": "ICR evidence and national administrative statistics",
        }
        return mapping.get(level, mapping["outcome"])
    if donor == "giz":
        return "Partner monitoring records, validation meetings, implementation review notes, and sustainability review notes"
    if donor in {"state_department", "us_state_department"}:
        if any(token in name for token in ("media", "journalist", "newsroom", "civil society", "resilience")):
            return "Partner monitoring records, editorial risk logs, and resilience review documentation"
        if _is_state_department_civic_indicator(name):
            return "Partner monitoring records, stakeholder verification notes, and risk review documentation"
        return "Program monitoring records, partner verification notes, and risk review documentation"
    if donor == "un_agencies":
        return "Partner monitoring records, field verification notes, and programme or sector review documentation"
    return "Monitoring records and verification documents"


def _apply_indicator_defaults(
    indicator: Dict[str, Any],
    *,
    donor_id: str,
    toc_statement_path: Optional[str] = None,
) -> Dict[str, Any]:
    out = dict(indicator)
    current_result_level = _normalize_result_level(out.get("result_level"))
    if not current_result_level and toc_statement_path:
        current_result_level = _infer_result_level_from_toc_path(toc_statement_path)
    if not current_result_level:
        current_result_level = "outcome"
    out["result_level"] = current_result_level

    raw_frequency = str(out.get("frequency") or "").strip().lower()
    if not raw_frequency:
        out["frequency"] = _default_frequency_for_donor(donor_id, result_level=current_result_level)
    else:
        out["frequency"] = raw_frequency

    raw_formula = str(out.get("formula") or "").strip()
    if not raw_formula:
        out["formula"] = _default_indicator_formula(str(out.get("name") or ""), result_level=current_result_level)
        out["formula"] = _default_indicator_formula(
            str(out.get("name") or ""),
            result_level=current_result_level,
            donor_id=donor_id,
        )
    else:
        out["formula"] = raw_formula

    raw_definition = str(out.get("definition") or "").strip()
    if not raw_definition:
        out["definition"] = _default_indicator_definition_for_donor(
            str(out.get("name") or ""),
            donor_id=donor_id,
            result_level=current_result_level,
        )
    else:
        out["definition"] = raw_definition

    raw_data_source = str(out.get("data_source") or "").strip()
    if not raw_data_source:
        out["data_source"] = _default_data_source_for_donor(
            donor_id,
            result_level=current_result_level,
            indicator_name=str(out.get("name") or ""),
        )
    else:
        out["data_source"] = raw_data_source

    if not isinstance(out.get("disaggregation"), list):
        out["disaggregation"] = _default_disaggregation(
            str(out.get("name") or ""),
            donor_id=donor_id,
            result_level=current_result_level,
        )

    raw_owner = str(out.get("owner") or "").strip()
    if not raw_owner:
        out["owner"] = _default_owner_for_donor(
            donor_id,
            result_level=current_result_level,
            indicator_name=str(out.get("name") or ""),
        )
    else:
        out["owner"] = raw_owner

    raw_mov = str(out.get("means_of_verification") or "").strip()
    if not raw_mov:
        out["means_of_verification"] = _default_means_of_verification_for_donor(
            donor_id,
            result_level=current_result_level,
            indicator_name=str(out.get("name") or ""),
        )
    else:
        out["means_of_verification"] = raw_mov
    return out


def _copy_optional_indicator_fields_from_hit(indicator: Dict[str, Any], hit: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(indicator)
    for key in (
        "indicator_code",
        "frequency",
        "disaggregation",
        "formula",
        "definition",
        "data_source",
        "owner",
        "means_of_verification",
        "result_level",
        "pdo_result_id",
        "partner_data_source",
        "line_of_effort",
    ):
        value = hit.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                continue
            updated[key] = cleaned
            continue
        if isinstance(value, (int, float, bool, list, dict)):
            updated[key] = value
    return updated


def _deterministic_indicators_from_toc(
    *,
    toc_payload: Dict[str, Any],
    retrieval_hits: list[Dict[str, Any]],
    namespace: str,
    donor_id: str = "",
    input_context: Optional[Dict[str, Any]] = None,
    max_indicators: int = 6,
) -> list[Dict[str, Any]]:
    candidates = _dedupe_toc_result_statements(
        _extract_toc_result_statements(toc_payload if isinstance(toc_payload, dict) else {}, "toc")
    )
    if not candidates:
        return []

    indicators: list[Dict[str, Any]] = []
    bounded_candidates = candidates[: max(1, max_indicators)]
    for idx, (statement_path, statement, _priority) in enumerate(bounded_candidates):
        hit, _score = _pick_best_mel_evidence_hit(statement, retrieval_hits)
        inferred_result_level = str(
            hit.get("result_level") or _infer_result_level_from_toc_path(statement_path)
        ).strip()
        name = str(
            hit.get("name")
            or _indicator_name_from_toc_statement(statement, idx=idx, result_level=inferred_result_level)
        ).strip()
        formula = str(
            hit.get("formula")
            or _default_indicator_formula(name, result_level=inferred_result_level, donor_id=donor_id)
        ).strip()
        baseline, target = _resolve_baseline_target(
            baseline_raw=hit.get("baseline") if hit else "",
            target_raw=hit.get("target") if hit else "",
            indicator_name=name,
            input_context=input_context or {},
            idx=idx,
            donor_id=donor_id,
            result_level=str(hit.get("result_level") or "").strip() or None,
            formula=formula,
        )
        citation = str(hit.get("label") or hit.get("source") or hit.get("doc_id") or namespace)
        justification = _deterministic_indicator_justification(
            donor_id=donor_id,
            statement_path=statement_path,
            result_level=inferred_result_level,
            statement=statement,
        )
        definition = _deterministic_definition_from_statement(
            donor_id=donor_id,
            result_level=inferred_result_level,
            statement=statement,
            indicator_name=name,
        )
        indicators.append(
            _apply_indicator_defaults(
                _copy_optional_indicator_fields_from_hit(
                    {
                        "indicator_id": str(hit.get("indicator_id") or f"IND_{idx + 1:03d}"),
                        "name": name or f"Results indicator {idx + 1}",
                        "justification": justification,
                        "definition": definition,
                        "citation": citation,
                        "baseline": baseline,
                        "target": target,
                        "evidence_excerpt": str(hit.get("excerpt") or statement)[:240],
                        "toc_statement_path": statement_path,
                    },
                    hit,
                ),
                donor_id=donor_id,
                toc_statement_path=statement_path,
            ),
        )
    return indicators


def _build_query_text(state: Dict[str, Any]) -> str:
    input_context = state_input_context(state)
    project = str(input_context.get("project") or "project")
    country = str(input_context.get("country") or "")
    toc = state.get("toc_draft", {}) or {}
    toc_payload = (toc.get("toc") or {}) if isinstance(toc, dict) else {}
    return build_stage_query_text(
        state=state,
        stage="mel",
        project=project,
        country=country,
        toc_payload=toc_payload,
    )


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _bounded_float(value: Any, *, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _rows(value: Any) -> list[list[Any]]:
    if not isinstance(value, list):
        return [[]]
    if value and not isinstance(value[0], list):
        return [value]
    return value


def _query_variants(state: Dict[str, Any], base_query: str, *, max_variants: int) -> list[str]:
    input_context = state_input_context(state)
    donor_id = state_donor_id(state, default="donor")
    donor_key = str(donor_id or "").strip().lower()
    project = str(input_context.get("project") or "").strip()
    country = str(input_context.get("country") or "").strip()
    problem = str(input_context.get("problem") or "").strip()
    expected_change = str(input_context.get("expected_change") or "").strip()
    toc = state.get("toc_draft", {}) or {}
    toc_payload = (toc.get("toc") or {}) if isinstance(toc, dict) else {}
    toc_summary = json.dumps(toc_payload, ensure_ascii=True)[:220] if isinstance(toc_payload, dict) else ""
    results_focus = ""
    if donor_key == "eu":
        results_focus = (
            f"{project} {country} eu logframe indicators means of verification baseline target "
            "specific objectives expected outcomes"
        ).strip()
    elif donor_key == "worldbank":
        results_focus = (
            f"{project} {country} world bank results framework pdo indicators "
            "intermediate results indicators implementation status results report"
        ).strip()

    candidates = [
        base_query.strip(),
        f"{project} {country} MEL indicators baseline target verification frequency".strip(),
        f"{project} {country} monitoring evaluation learning results framework assumptions".strip(),
        results_focus,
        f"{project} {country} problem {problem[:160]} expected change {expected_change[:160]}".strip(),
        f"{project} {country} toc summary {toc_summary}".strip(),
    ]
    unique: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        query = str(raw or "").strip()
        if not query:
            continue
        marker = query.lower()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(query)
        if len(unique) >= max_variants:
            break
    return unique or [base_query]


def _retrieval_confidence(raw_distance: Any, idx: int) -> float:
    if isinstance(raw_distance, (int, float)):
        return round(max(0.0, min(1.0, 1.0 / (1.0 + float(raw_distance)))), 4)
    return round(max(0.1, 1.0 - (idx * 0.2)), 4)


def _collect_retrieval_hits(
    result: Dict[str, Any],
    *,
    namespace: str,
    namespace_normalized: str,
    collection: str,
    query_text: str,
    query_variants: list[str],
    top_k: int,
    min_hit_confidence: float,
) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    docs_rows = _rows((result or {}).get("documents"))
    metas_rows = _rows((result or {}).get("metadatas"))
    ids_rows = _rows((result or {}).get("ids"))
    distances_rows = _rows((result or {}).get("distances"))

    base_tokens = _token_set(query_text)
    best_by_signature: dict[tuple[Any, ...], Dict[str, Any]] = {}
    for q_idx, query_variant in enumerate(query_variants):
        docs = docs_rows[q_idx] if q_idx < len(docs_rows) else []
        metas = metas_rows[q_idx] if q_idx < len(metas_rows) else []
        ids = ids_rows[q_idx] if q_idx < len(ids_rows) else []
        distances = distances_rows[q_idx] if q_idx < len(distances_rows) else []
        query_tokens = _token_set(query_variant)
        for idx, doc in enumerate(docs):
            meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
            retrieval_rank = idx + 1
            raw_doc_id = meta.get("doc_id") or meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None)
            raw_chunk_id = meta.get("chunk_id") or raw_doc_id
            doc_id = str(raw_doc_id or "").strip()
            chunk_id = str(raw_chunk_id or "").strip()
            if not doc_id and chunk_id:
                doc_id = chunk_id
            if not chunk_id and doc_id:
                chunk_id = doc_id
            if not doc_id:
                doc_id = f"{namespace_normalized}#q{q_idx + 1}-hit-{retrieval_rank}"
            if not chunk_id:
                chunk_id = doc_id
            source = citation_source_from_metadata(meta)
            excerpt = str(doc or "")[:240]
            raw_distance = distances[idx] if idx < len(distances) else None
            retrieval_distance = round(float(raw_distance), 6) if isinstance(raw_distance, (int, float)) else None
            retrieval_conf = _retrieval_confidence(raw_distance, idx)
            hit_tokens = _token_set(excerpt) | _token_set(str(source or ""))
            query_overlap = len(query_tokens & hit_tokens) / max(1, len(query_tokens))
            base_overlap = len(base_tokens & hit_tokens) / max(1, len(base_tokens))
            rank_penalty = min(0.18, idx * 0.03)
            rerank_score = max(
                0.0,
                (base_overlap * 0.35) + (query_overlap * 0.25) + (retrieval_conf * 0.40) - rank_penalty,
            )

            hit = {
                "rank": retrieval_rank,
                "retrieval_rank": retrieval_rank,
                "query_variant_index": q_idx + 1,
                "query_variant": query_variant,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "indicator_id": meta.get("indicator_id"),
                "name": meta.get("name"),
                "indicator_code": meta.get("indicator_code"),
                "baseline": meta.get("baseline"),
                "target": meta.get("target"),
                "frequency": meta.get("frequency"),
                "disaggregation": meta.get("disaggregation"),
                "formula": meta.get("formula"),
                "definition": meta.get("definition"),
                "data_source": meta.get("data_source"),
                "result_level": meta.get("result_level"),
                "pdo_result_id": meta.get("pdo_result_id"),
                "partner_data_source": meta.get("partner_data_source"),
                "line_of_effort": meta.get("line_of_effort"),
                "source": source,
                "page": meta.get("page"),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
                "chunk": meta.get("chunk"),
                "label": citation_label_from_metadata(meta, namespace=namespace, rank=retrieval_rank),
                "excerpt": excerpt,
                "retrieval_confidence": retrieval_conf,
                "retrieval_distance": retrieval_distance,
                "rerank_score": round(min(1.0, rerank_score), 4),
                "namespace": namespace,
                "namespace_normalized": namespace_normalized,
                "collection": collection,
            }
            traceability_status = citation_traceability_status(hit)
            hit["traceability_status"] = traceability_status
            hit["traceability_complete"] = traceability_status == "complete"

            signature = (hit.get("doc_id"), hit.get("chunk_id"), hit.get("source"), hit.get("page"))
            current = best_by_signature.get(signature)
            if current is None:
                best_by_signature[signature] = hit
                continue
            current_key = (
                float(current.get("rerank_score") or 0.0),
                float(current.get("retrieval_confidence") or 0.0),
                -int(current.get("retrieval_rank") or 999),
            )
            candidate_key = (
                float(hit.get("rerank_score") or 0.0),
                float(hit.get("retrieval_confidence") or 0.0),
                -int(hit.get("retrieval_rank") or 999),
            )
            if candidate_key > current_key:
                best_by_signature[signature] = hit

    ranked = sorted(
        best_by_signature.values(),
        key=lambda hit: (
            float(hit.get("rerank_score") or 0.0),
            float(hit.get("retrieval_confidence") or 0.0),
            -int(hit.get("retrieval_rank") or 999),
            -int(hit.get("query_variant_index") or 999),
        ),
        reverse=True,
    )
    filtered = [
        hit
        for hit in ranked
        if float(hit.get("retrieval_confidence") or 0.0) >= min_hit_confidence
        or float(hit.get("rerank_score") or 0.0) >= min_hit_confidence
    ]
    if not filtered and ranked:
        filtered = ranked[:1]

    hits = filtered[:top_k]
    for idx, hit in enumerate(hits):
        hit["rank"] = idx + 1

    diagnostics = {
        "candidate_hits_count": len(ranked),
        "filtered_out_low_confidence": max(0, len(ranked) - len(filtered)),
        "avg_rerank_score": (
            round(
                sum(float(hit.get("rerank_score") or 0.0) for hit in hits) / len(hits),
                4,
            )
            if hits
            else None
        ),
    }
    return hits, diagnostics


def _token_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z0-9_]+", text.lower()) if len(token) > 2}


def _pick_best_mel_evidence_hit(statement: str, hits: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
    statement_tokens = _token_set(statement)
    best_hit: Dict[str, Any] = {}
    best_score = 0.0
    for idx, hit in enumerate(hits):
        excerpt_tokens = _token_set(str(hit.get("excerpt") or ""))
        if statement_tokens:
            overlap = len(statement_tokens & excerpt_tokens) / max(1, len(statement_tokens))
        else:
            overlap = 0.0
        retrieval_confidence = float(hit.get("retrieval_confidence") or 0.0)
        rerank_score = float(hit.get("rerank_score") or 0.0)
        rank_penalty = min(0.2, idx * 0.03)
        score = max(0.0, (overlap * 0.5) + (retrieval_confidence * 0.3) + (rerank_score * 0.2) - rank_penalty)
        if score > best_score:
            best_score = score
            best_hit = hit
    return best_hit, round(min(1.0, best_score), 4)


def _mel_grounded_confidence_bonus(hit: Dict[str, Any], *, traceability_status: str) -> float:
    if not hit or traceability_status != "complete":
        return 0.0
    bonus = 0.0
    retrieval_rank = hit.get("retrieval_rank") or hit.get("rank")
    try:
        retrieval_rank_int = int(retrieval_rank)
    except (TypeError, ValueError):
        retrieval_rank_int = 999
    retrieval_confidence = float(hit.get("retrieval_confidence") or 0.0)
    if retrieval_rank_int <= 1:
        bonus += 0.05
    if retrieval_confidence >= 0.4:
        bonus += 0.02
    if retrieval_confidence >= 0.45:
        bonus += 0.02
    if hit.get("doc_id") and hit.get("chunk_id"):
        bonus += 0.01
    return min(0.1, round(bonus, 4))


def _is_placeholder_baseline_target(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in MEL_PLACEHOLDER_BASELINE_TARGET_VALUES


def _input_context_int(input_context: Dict[str, Any], *keys: str) -> Optional[int]:
    for key in keys:
        raw = input_context.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)
        if isinstance(raw, str):
            match = re.search(r"[-+]?\d+", raw.replace(",", ""))
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    continue
    return None


def _baseline_target_seed(input_context: Dict[str, Any]) -> int:
    duration_months = _input_context_int(input_context, "duration_months", "duration", "project_duration_months")
    budget = _input_context_int(input_context, "budget", "budget_usd", "grant_amount")
    participants = _input_context_int(input_context, "target_population_size", "beneficiary_count", "participants")

    seed = 120
    if isinstance(duration_months, int) and duration_months > 0:
        seed = max(seed, min(600, duration_months * 12))
    if isinstance(budget, int) and budget > 0:
        seed = max(seed, min(1200, max(60, budget // 20000)))
    if isinstance(participants, int) and participants > 0:
        seed = max(seed, min(1200, participants))
    return max(40, seed)


def _donor_target_profile(donor_id: str) -> Dict[str, int]:
    token = str(donor_id or "").strip().lower()
    base = {
        "percent_target": 25,
        "policy_target": 3,
        "institution_target": 5,
        "organization_target": 4,
        "time_improvement_percent": 30,
        "people_floor": 120,
    }
    overrides: Dict[str, Dict[str, int]] = {
        "usaid": {
            "percent_target": 30,
            "policy_target": 4,
            "institution_target": 6,
            "organization_target": 5,
            "time_improvement_percent": 35,
            "people_floor": 150,
        },
        "eu": {
            "percent_target": 20,
            "policy_target": 3,
            "institution_target": 4,
            "organization_target": 4,
            "time_improvement_percent": 25,
            "people_floor": 100,
        },
        "worldbank": {
            "percent_target": 20,
            "policy_target": 2,
            "institution_target": 8,
            "organization_target": 5,
            "time_improvement_percent": 25,
            "people_floor": 130,
        },
        "giz": {
            "percent_target": 22,
            "policy_target": 3,
            "institution_target": 5,
            "organization_target": 4,
            "time_improvement_percent": 25,
            "people_floor": 120,
        },
        "state_department": {
            "percent_target": 25,
            "policy_target": 4,
            "institution_target": 5,
            "organization_target": 6,
            "time_improvement_percent": 30,
            "people_floor": 110,
        },
        "us_state_department": {
            "percent_target": 25,
            "policy_target": 4,
            "institution_target": 5,
            "organization_target": 6,
            "time_improvement_percent": 30,
            "people_floor": 110,
        },
    }
    selected = overrides.get(token, {})
    out = dict(base)
    out.update(selected)
    return out


def _is_people_indicator(name: str) -> bool:
    return any(token in name for token in ("train", "certif", "capacity", "skills", "official", "staff", "participant"))


def _is_policy_indicator(name: str) -> bool:
    return any(token in name for token in ("policy", "regulation", "protocol", "sop", "guideline"))


def _is_institution_indicator(name: str) -> bool:
    return any(
        token in name
        for token in ("institution", "agency", "ministry", "municipal", "department", "government", "service center")
    )


def _is_organization_indicator(name: str) -> bool:
    return any(
        token in name
        for token in ("organization", "organisation", "media outlet", "newsroom", "cso", "ngo", "civil society")
    )


def _is_state_department_organizational_indicator(name: str) -> bool:
    if _is_organization_indicator(name):
        return True
    return any(
        token in name
        for token in (
            "independent media",
            "media resilience",
            "media ecosystem",
            "journalist",
            "journalism",
            "local media",
        )
    )


def _is_state_department_civic_indicator(name: str) -> bool:
    lowered = str(name or "").lower()
    return any(
        token in lowered
        for token in (
            "civic",
            "rights",
            "information integrity",
            "public diplomacy",
            "governance",
            "accountability",
        )
    )


def _indicator_count_unit_from_formula(formula: str, *, donor_id: str = "", indicator_name: str = "") -> str:
    lowered = " ".join(f"{formula} {indicator_name}".split()).lower()
    donor = str(donor_id or "").strip().lower()
    if any(token in lowered for token in ("civil servants", "government officials", "officials")):
        return "civil servants"
    if "individuals" in lowered:
        return "individuals"
    if "people" in lowered or (
        donor == "usaid" and any(token in lowered for token in ("skills", "training", "capacity"))
    ):
        return "people"
    if "institutions" in lowered or "agencies" in lowered:
        return "institutions"
    if "organizations" in lowered or "organisations" in lowered:
        return "organizations"
    if "smes" in lowered or "enterprises" in lowered:
        return "smes"
    if "policies" in lowered or "protocols" in lowered:
        return "policies"
    return ""


def _suggest_baseline_target(
    *,
    indicator_name: str,
    input_context: Dict[str, Any],
    idx: int,
    donor_id: str = "",
    result_level: Optional[str] = None,
    existing_baseline: str = "",
    formula: str = "",
) -> tuple[str, str]:
    name = str(indicator_name or "").lower()
    formula_text = str(formula or "").strip()
    seed = _baseline_target_seed(input_context)
    profile = _donor_target_profile(donor_id)
    percent_target = int(profile.get("percent_target") or 25)
    policy_target = int(profile.get("policy_target") or 3)
    institution_target = int(profile.get("institution_target") or 5)
    organization_target = int(profile.get("organization_target") or 4)
    time_improvement_percent = int(profile.get("time_improvement_percent") or 30)
    people_floor = int(profile.get("people_floor") or 120)
    level = str(result_level or "").strip().lower()
    if level == "impact":
        percent_target = min(40, percent_target + 5)
        institution_target = max(institution_target, 6)
        organization_target = max(organization_target, 5)
    elif level == "output":
        percent_target = max(15, percent_target - 5)
    if any(token in name for token in ("time", "days", "duration", "delay", "processing", "turnaround")):
        target_days = max(1, int(round(90 * (1 - (time_improvement_percent / 100)))))
        return "90 days", f"{target_days} days"
    if any(token in name for token in ("percent", "%", "rate", "share", "coverage")):
        return "0%", f"{percent_target}%"
    formula_unit = _indicator_count_unit_from_formula(formula_text, donor_id=donor_id, indicator_name=indicator_name)
    if formula_unit == "civil servants":
        return "0 civil servants", f"{max(seed, people_floor)} civil servants"
    if formula_unit == "individuals":
        return "0 individuals", f"{max(seed, people_floor)} individuals"
    if formula_unit == "people":
        return "0 people", f"{max(seed, people_floor)} people"
    if formula_unit == "institutions":
        return "0 institutions", f"{institution_target} institutions"
    if formula_unit == "organizations":
        return "0 organizations", f"{organization_target} organizations"
    if formula_unit == "smes":
        return "0 SMEs", f"{max(organization_target, institution_target)} SMEs"
    if formula_unit == "policies":
        return "0 policies", f"{policy_target} policies"
    if donor_id in {"state_department", "us_state_department"} and _is_state_department_organizational_indicator(name):
        return "0 organizations", f"{organization_target} organizations"
    if _is_policy_indicator(name):
        return "0 policies", f"{policy_target} policies"
    if _is_institution_indicator(name):
        return "0 institutions", f"{institution_target} institutions"
    if donor_id in {"eu", "worldbank"} and any(
        token in name for token in ("performance score", "governance score", "service quality", "adoption")
    ):
        return "0 institutions", f"{institution_target} institutions"
    if _is_people_indicator(name):
        return "0 people", f"{max(seed, people_floor)} people"
    if donor_id in {"state_department", "us_state_department"} and _is_state_department_organizational_indicator(name):
        return "0 organizations", f"{organization_target} organizations"
    if _is_organization_indicator(name):
        return "0 organizations", f"{organization_target} organizations"

    if existing_baseline:
        baseline_l = existing_baseline.lower()
        if "%" in baseline_l:
            return existing_baseline, f"{percent_target}%"
        number_match = re.search(r"(\d+(?:\.\d+)?)", baseline_l.replace(",", ""))
        if number_match:
            baseline_num = float(number_match.group(1))
            if any(token in name for token in ("time", "days", "duration", "delay", "processing", "turnaround")):
                target_num = max(1.0, baseline_num * (1 - (time_improvement_percent / 100)))
            else:
                target_num = baseline_num + max(5.0, baseline_num * 0.3)
            if target_num.is_integer():
                target_repr = str(int(target_num))
            else:
                target_repr = f"{target_num:.1f}"
            unit = re.sub(r"[-+]?\d+(?:\.\d+)?", "", existing_baseline).strip()
            if unit:
                target_repr = f"{target_repr} {unit}".strip()
            return existing_baseline, target_repr

    return "0", str(seed + (idx * 20))


def _resolve_baseline_target(
    *,
    baseline_raw: Any,
    target_raw: Any,
    indicator_name: str,
    input_context: Dict[str, Any],
    idx: int,
    donor_id: str = "",
    result_level: Optional[str] = None,
    formula: str = "",
) -> tuple[str, str]:
    baseline = str(baseline_raw or "").strip()
    target = str(target_raw or "").strip()

    baseline_placeholder = _is_placeholder_baseline_target(baseline)
    target_placeholder = _is_placeholder_baseline_target(target)
    if baseline_placeholder and target_placeholder:
        return _suggest_baseline_target(
            indicator_name=indicator_name,
            input_context=input_context,
            idx=idx,
            donor_id=donor_id,
            result_level=result_level,
            formula=formula,
        )
    if baseline_placeholder:
        suggested_baseline, _ = _suggest_baseline_target(
            indicator_name=indicator_name,
            input_context=input_context,
            idx=idx,
            donor_id=donor_id,
            result_level=result_level,
            existing_baseline=target,
            formula=formula,
        )
        return suggested_baseline, target
    if target_placeholder:
        _, suggested_target = _suggest_baseline_target(
            indicator_name=indicator_name,
            input_context=input_context,
            idx=idx,
            donor_id=donor_id,
            result_level=result_level,
            existing_baseline=baseline,
            formula=formula,
        )
        return baseline, suggested_target
    return baseline, target


def _indicator_from_hit(
    hit: Dict[str, Any],
    *,
    idx: int,
    namespace: str,
    donor_id: str = "",
    input_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    name = str(hit.get("name") or f"Indicator from {namespace} #{idx + 1}")
    toc_statement_path = str(hit.get("toc_statement_path") or "").strip() or ""
    result_level = str(hit.get("result_level") or "").strip() or None
    formula = str(
        hit.get("formula") or _default_indicator_formula(name, result_level=result_level or "", donor_id=donor_id)
    ).strip()
    baseline, target = _resolve_baseline_target(
        baseline_raw=hit.get("baseline"),
        target_raw=hit.get("target"),
        indicator_name=name,
        input_context=input_context or {},
        idx=idx,
        donor_id=donor_id,
        result_level=result_level,
        formula=formula,
    )
    justification = str(hit.get("justification") or "").strip()
    if _is_generic_indicator_justification(justification):
        justification = _retrieval_indicator_justification(
            donor_id=donor_id,
            namespace=namespace,
            toc_statement_path=toc_statement_path or f"retrieval_hit[{idx}]",
            result_level=result_level or "",
            indicator_name=name,
        )
    definition = str(hit.get("definition") or "").strip()
    if not definition:
        definition = _retrieval_definition_from_hit(
            donor_id=donor_id,
            namespace=namespace,
            toc_statement_path=toc_statement_path or f"retrieval_hit[{idx}]",
            result_level=result_level or "",
            indicator_name=name,
            excerpt=str(hit.get("excerpt") or ""),
            source=str(hit.get("source") or ""),
        )
    indicator: Dict[str, Any] = {
        "indicator_id": str(hit.get("indicator_id") or f"IND_{idx + 1:03d}"),
        "name": name,
        "justification": justification,
        "definition": definition,
        "citation": str(hit.get("label") or namespace),
        "baseline": baseline,
        "target": target,
        "evidence_excerpt": str(hit.get("excerpt") or "")[:240],
    }
    enriched = _copy_optional_indicator_fields_from_hit(indicator, hit)
    return _apply_indicator_defaults(
        enriched,
        donor_id=donor_id,
        toc_statement_path=toc_statement_path or None,
    )


def _normalize_indicator_item(
    item: Any,
    *,
    idx: int,
    namespace: str,
    donor_id: str = "",
    input_context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    indicator_id = str(item.get("indicator_id") or f"IND_{idx + 1:03d}").strip() or f"IND_{idx + 1:03d}"
    name = str(item.get("name") or "").strip() or f"Indicator {idx + 1}"
    toc_statement_path = str(item.get("toc_statement_path") or "").strip() or ""
    result_level = str(item.get("result_level") or "").strip() or None
    justification = str(item.get("justification") or "").strip()
    if _is_generic_indicator_justification(justification):
        justification = _retrieval_indicator_justification(
            donor_id=donor_id,
            namespace=namespace,
            toc_statement_path=toc_statement_path or f"normalized_item[{idx}]",
            result_level=result_level or "",
            indicator_name=name,
        )
    definition = str(item.get("definition") or "").strip()
    if not definition:
        definition = _retrieval_definition_from_hit(
            donor_id=donor_id,
            namespace=namespace,
            toc_statement_path=toc_statement_path or f"normalized_item[{idx}]",
            result_level=result_level or "",
            indicator_name=name,
            excerpt=str(item.get("evidence_excerpt") or ""),
            source=str(item.get("citation") or ""),
        )
    citation = str(item.get("citation") or "").strip() or namespace
    formula = str(
        item.get("formula") or _default_indicator_formula(name, result_level=result_level or "", donor_id=donor_id)
    ).strip()
    baseline, target = _resolve_baseline_target(
        baseline_raw=item.get("baseline"),
        target_raw=item.get("target"),
        indicator_name=name,
        input_context=input_context or {},
        idx=idx,
        donor_id=donor_id,
        result_level=result_level,
        formula=formula,
    )
    evidence_excerpt = str(item.get("evidence_excerpt") or "").strip() or None
    normalized: Dict[str, Any] = {
        "indicator_id": indicator_id,
        "name": name,
        "justification": justification,
        "definition": definition,
        "citation": citation,
        "baseline": baseline,
        "target": target,
        "evidence_excerpt": evidence_excerpt,
    }
    canonical_keys = {
        "indicator_id",
        "name",
        "justification",
        "citation",
        "baseline",
        "target",
        "evidence_excerpt",
    }
    for key, value in item.items():
        if key in canonical_keys:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                continue
            normalized[key] = cleaned
            continue
        if isinstance(value, (int, float, bool, list, dict)):
            normalized[key] = value
    return _apply_indicator_defaults(
        normalized,
        donor_id=donor_id,
        toc_statement_path=toc_statement_path or None,
    )


def _fallback_indicator(
    namespace: str,
    *,
    donor_id: str = "",
    input_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    baseline, target = _resolve_baseline_target(
        baseline_raw="",
        target_raw="",
        indicator_name="Project Output Indicator",
        input_context=input_context or {},
        idx=0,
        donor_id=donor_id,
        result_level="output",
    )
    return _apply_indicator_defaults(
        {
            "indicator_id": "IND_001",
            "name": "Project Output Indicator",
            "justification": "Fallback indicator used because donor-specific RAG retrieval returned no grounded results.",
            "citation": namespace,
            "baseline": baseline,
            "target": target,
            "result_level": "output",
            "evidence_excerpt": None,
        },
        donor_id=donor_id,
        toc_statement_path="toc.outputs[0]",
    )


def _normalize_llm_indicators(
    raw_indicators: Any,
    *,
    namespace: str,
    donor_id: str = "",
    input_context: Optional[Dict[str, Any]] = None,
) -> list[Dict[str, Any]]:
    if not isinstance(raw_indicators, list):
        return []
    indicators: list[Dict[str, Any]] = []
    for idx, item in enumerate(raw_indicators):
        normalized = _normalize_indicator_item(
            item,
            idx=idx,
            namespace=namespace,
            donor_id=donor_id,
            input_context=input_context,
        )
        if normalized is None:
            continue
        indicators.append(normalized)
    return indicators


def _llm_structured_mel(
    *,
    schema_cls: Type[BaseModel],
    model_name: str,
    system_prompt: str,
    donor_id: str,
    project: str,
    country: str,
    input_context: Dict[str, Any],
    toc_payload: Dict[str, Any],
    revision_hint: str,
    evidence_hits: Iterable[Dict[str, Any]],
    schema_contract_hint: str = "",
    retrieval_trace_hint: Optional[str] = None,
    validation_error_hint: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    llm_kwargs = chat_openai_init_kwargs(model=model_name, temperature=0.1)
    if llm_kwargs is None:
        return None, None, openai_compatible_missing_reason()

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        toc_summary = json.dumps(toc_payload or {}, ensure_ascii=True)[:1600]
        evidence_lines: list[str] = []
        for hit in list(evidence_hits)[:MEL_MAX_EVIDENCE_PROMPT_HITS]:
            label = str(hit.get("label") or hit.get("source") or "evidence").strip()
            excerpt = str(hit.get("excerpt") or "").strip()[:220]
            page = hit.get("page")
            page_hint = f" (page {page})" if page is not None else ""
            conf = hit.get("retrieval_confidence")
            conf_hint = f" [conf={float(conf):.2f}]" if isinstance(conf, (int, float)) else ""
            evidence_lines.append(f"- {label}{page_hint}{conf_hint}: {excerpt}")

        human_prompt = (
            "Generate a MEL/LogFrame indicator set as structured JSON.\n\n"
            f"Donor: {donor_id}\n"
            f"Project: {project}\n"
            f"Country: {country}\n"
            f"Input context JSON: {_safe_json(input_context)}\n"
            f"ToC summary: {toc_summary}\n"
        )
        if schema_contract_hint:
            human_prompt += "\nSchema contract (follow field names and types):\n"
            human_prompt += f"{schema_contract_hint}\n"
        if retrieval_trace_hint:
            human_prompt += f"Retrieval trace summary: {retrieval_trace_hint}\n"
        if revision_hint:
            human_prompt += f"Revision guidance: {revision_hint[:400]}\n"
        if validation_error_hint:
            human_prompt += (
                "Previous structured output failed validation; fix it. "
                f"Validation errors: {str(validation_error_hint)[:500]}\n"
            )
        if evidence_lines:
            human_prompt += "\nRetrieved donor evidence:\n" + "\n".join(evidence_lines) + "\n"
        human_prompt += (
            "\nRequirements:\n"
            "- Return at least 1 and up to 6 indicators.\n"
            "- Do not invent source docs; use provided evidence labels in citation fields when possible.\n"
            "- Keep indicator ids stable and concise.\n"
            "- Avoid placeholders like TBD/placeholder in baseline/target when context suggests concrete values.\n"
            "- Return structured object only.\n"
        )

        llm = ChatOpenAI(**llm_kwargs)
        structured = llm.with_structured_output(schema_cls)
        result = structured.invoke(
            [
                SystemMessage(content=system_prompt or "You are a MEL specialist drafting indicator sets."),
                HumanMessage(content=human_prompt),
            ]
        )
        if isinstance(result, BaseModel):
            return _model_dump(result), f"llm:{model_name}", None
        if isinstance(result, dict):
            return result, f"llm:{model_name}", None
        return None, None, "LLM structured output returned unsupported type"
    except Exception as exc:  # pragma: no cover - exercised only when LLM deps configured
        return None, None, str(exc)


def _build_mel_citations(
    *,
    indicators: list[Dict[str, Any]],
    evidence_hits: Iterable[Dict[str, Any]],
    namespace: str,
    namespace_normalized: str,
    donor_id: str,
    use_strategy_reference_when_no_hits: bool = False,
) -> list[Dict[str, Any]]:
    hits = [h for h in evidence_hits if isinstance(h, dict)]
    base_threshold = _bounded_float(
        getattr(config.rag, "mel_citation_high_confidence_threshold", MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD),
        default=MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD,
        low=0.0,
        high=1.0,
    )
    donor_key = str(donor_id or "").strip().lower()
    threshold = _bounded_float(
        MEL_CITATION_DONOR_THRESHOLD_OVERRIDES.get(donor_key, base_threshold),
        default=base_threshold,
        low=0.0,
        high=1.0,
    )
    citations: list[Dict[str, Any]] = []
    for idx, indicator in enumerate(indicators):
        indicator_id = str(indicator.get("indicator_id") or f"IND_{idx + 1:03d}")
        name = str(indicator.get("name") or "")
        justification = str(indicator.get("justification") or "")
        toc_statement_path = str(indicator.get("toc_statement_path") or "").strip() or None
        result_level = str(indicator.get("result_level") or "").strip() or None
        statement = f"{name}. {justification}".strip()
        hit: Dict[str, Any]
        confidence: float
        if hits:
            citation_hint = str(indicator.get("citation") or "").strip()
            matched_hit = next(
                (
                    candidate
                    for candidate in hits
                    if str(candidate.get("label") or "").strip() == citation_hint
                    or str(candidate.get("source") or "").strip() == citation_hint
                    or str(candidate.get("doc_id") or "").strip() == citation_hint
                    or str(candidate.get("chunk_id") or "").strip() == citation_hint
                ),
                None,
            )
            if isinstance(matched_hit, dict):
                hit = matched_hit
                confidence = round(
                    max(
                        float(hit.get("retrieval_confidence") or 0.0),
                        float(hit.get("rerank_score") or 0.0),
                    ),
                    4,
                )
            else:
                hit, confidence = _pick_best_mel_evidence_hit(statement, hits)
        else:
            hit, confidence = {}, 0.1
        if hit:
            traceability_status = citation_traceability_status(hit)
        elif use_strategy_reference_when_no_hits:
            traceability_status = "complete"
        else:
            traceability_status = "missing"
        if hit:
            confidence = round(
                min(
                    1.0,
                    float(confidence) + _mel_grounded_confidence_bonus(hit, traceability_status=traceability_status),
                ),
                4,
            )
        if hit and traceability_status == "complete" and confidence >= threshold:
            citation_type = "rag_result"
        elif hit:
            citation_type = "rag_low_confidence"
        elif use_strategy_reference_when_no_hits:
            citation_type = "strategy_reference"
            confidence = 0.75
        else:
            citation_type = "fallback_namespace"
            confidence = 0.1
        label = str(hit.get("label") or indicator.get("citation") or namespace)
        indicator_doc_id = f"strategy::{namespace_normalized}::{indicator_id.lower()}"
        citations.append(
            {
                "stage": "mel",
                "citation_type": citation_type,
                "namespace": namespace,
                "namespace_normalized": namespace_normalized,
                "doc_id": (
                    hit.get("doc_id") if hit else (indicator_doc_id if use_strategy_reference_when_no_hits else None)
                ),
                "source": (
                    hit.get("source")
                    if hit
                    else (f"strategy::{donor_id}" if use_strategy_reference_when_no_hits else None)
                ),
                "page": hit.get("page"),
                "page_start": hit.get("page_start"),
                "page_end": hit.get("page_end"),
                "chunk": hit.get("chunk"),
                "chunk_id": (
                    hit.get("chunk_id") or hit.get("doc_id")
                    if hit
                    else (indicator_doc_id if use_strategy_reference_when_no_hits else None)
                ),
                "label": label,
                "used_for": indicator_id,
                "statement_path": toc_statement_path,
                "toc_statement_path": toc_statement_path,
                "result_level": result_level,
                "statement": statement[:240] or None,
                "excerpt": str(hit.get("excerpt") or indicator.get("evidence_excerpt") or "")[:240] or None,
                "citation_confidence": round(confidence, 4),
                "evidence_score": round(confidence, 4),
                "evidence_rank": hit.get("rank"),
                "retrieval_rank": hit.get("retrieval_rank") or hit.get("rank"),
                "retrieval_confidence": hit.get("retrieval_confidence") if hit else confidence,
                "retrieval_distance": hit.get("retrieval_distance") if hit else None,
                "confidence_threshold": threshold,
                "traceability_status": traceability_status,
                "traceability_complete": traceability_status == "complete",
            }
        )
    return citations


def mel_assign_indicators(state: Dict[str, Any]) -> Dict[str, Any]:
    """Назначает MEL индикаторы c RAG retrieval и optional LLM structured generation."""
    normalize_state_contract(state)
    strategy = state_donor_strategy(state)
    if not strategy:
        state.setdefault("errors", []).append("MEL cannot run without donor_strategy")
        return state

    namespace = state_rag_namespace(state, default=strategy.get_rag_collection())
    namespace_trace = vector_store.namespace_trace(namespace)
    namespace_normalized = namespace_trace["namespace_normalized"]
    collection = namespace_trace["collection"]
    donor_id = state_donor_id(state, default=str(getattr(strategy, "donor_id", "donor")))
    query_text = _build_query_text(state)
    top_k = _bounded_int(
        getattr(config.rag, "mel_top_k", getattr(config.rag, "default_top_k", 5)),
        default=5,
        low=1,
        high=12,
    )
    rerank_pool_size = _bounded_int(
        getattr(config.rag, "mel_rerank_pool_size", max(top_k, 10)),
        default=max(top_k, 10),
        low=top_k,
        high=36,
    )
    query_variants_limit = _bounded_int(
        getattr(config.rag, "mel_query_variants", 3),
        default=3,
        low=1,
        high=6,
    )
    min_hit_confidence = _bounded_float(
        getattr(config.rag, "mel_min_hit_confidence", 0.3),
        default=0.3,
        low=0.0,
        high=1.0,
    )
    query_variants = _query_variants(state, query_text, max_variants=query_variants_limit)
    input_context = state_input_context(state)
    schema_cls = _resolve_mel_schema_cls(strategy)
    schema_contract_hint = _schema_contract_hint(schema_cls)
    project = str(input_context.get("project") or "TBD project")
    country = str(input_context.get("country") or "TBD")
    toc = state.get("toc_draft", {}) or {}
    toc_payload = (toc.get("toc") or {}) if isinstance(toc, dict) else {}
    revision_hint = state_revision_hint(state)

    retrieval_hits: list[Dict[str, Any]] = []
    rag_trace: Dict[str, Any] = {
        "namespace": namespace,
        "namespace_normalized": namespace_normalized,
        "collection": collection,
        "query": query_text,
        "query_variants": query_variants,
        "query_variants_count": len(query_variants),
        "top_k": top_k,
        "rerank_pool_size": rerank_pool_size,
        "min_hit_confidence": round(min_hit_confidence, 3),
        "used_results": 0,
    }
    llm_mode = state_llm_mode(state, default=False)
    llm_available = openai_compatible_llm_available()
    llm_attempted = False
    llm_repair_attempted = False
    llm_selected_model: Optional[str] = None
    llm_models_tried: list[str] = []
    llm_failure_reasons: list[str] = []
    llm_error: Optional[str] = None
    generation_engine = "deterministic:retrieval_template"
    fallback_used = False
    fallback_class = "deterministic_mode"
    deterministic_source = "retrieval_template"

    try:
        result = vector_store.query(namespace=namespace, query_texts=query_variants, n_results=rerank_pool_size)
        retrieval_hits, retrieval_diag = _collect_retrieval_hits(
            result if isinstance(result, dict) else {},
            namespace=namespace,
            namespace_normalized=namespace_normalized,
            collection=collection,
            query_text=query_text,
            query_variants=query_variants,
            top_k=top_k,
            min_hit_confidence=min_hit_confidence,
        )
        rag_trace.update(retrieval_diag)
        rag_trace["used_results"] = len(retrieval_hits)
        if retrieval_hits:
            rag_trace["hits"] = [
                {
                    "retrieval_rank": int(hit.get("retrieval_rank") or hit.get("rank") or 0),
                    "query_variant_index": int(hit.get("query_variant_index") or 0),
                    "doc_id": hit.get("doc_id"),
                    "source": hit.get("source"),
                    "page": hit.get("page"),
                    "chunk_id": hit.get("chunk_id"),
                    "retrieval_confidence": hit.get("retrieval_confidence"),
                    "retrieval_distance": hit.get("retrieval_distance"),
                    "rerank_score": hit.get("rerank_score"),
                    "traceability_status": hit.get("traceability_status"),
                    "traceability_complete": hit.get("traceability_complete"),
                    "namespace": hit.get("namespace"),
                    "namespace_normalized": hit.get("namespace_normalized"),
                    "collection": hit.get("collection"),
                }
                for hit in retrieval_hits
            ]
            traceability_statuses = [citation_traceability_status(hit) for hit in retrieval_hits]
            rag_trace["traceability_counts"] = {
                "complete": sum(1 for status in traceability_statuses if status == "complete"),
                "partial": sum(1 for status in traceability_statuses if status == "partial"),
                "missing": sum(1 for status in traceability_statuses if status == "missing"),
            }
            rag_trace["avg_retrieval_confidence"] = round(
                sum(float(hit.get("retrieval_confidence") or 0.0) for hit in retrieval_hits) / len(retrieval_hits),
                4,
            )
    except Exception as exc:
        state.setdefault("errors", []).append(f"MEL RAG query failed: {exc}")
        rag_trace["error"] = str(exc)

    retrieval_trace_hint: Optional[str] = None
    if retrieval_hits:
        retrieval_trace_hint = _safe_json(
            {
                "used_results": int(rag_trace.get("used_results") or 0),
                "query_variants_count": int(rag_trace.get("query_variants_count") or len(query_variants)),
                "avg_retrieval_confidence": rag_trace.get("avg_retrieval_confidence"),
                "traceability_counts": rag_trace.get("traceability_counts") or {},
                "hits": [
                    {
                        "label": hit.get("label"),
                        "source": hit.get("source"),
                        "page": hit.get("page"),
                        "retrieval_confidence": hit.get("retrieval_confidence"),
                        "rerank_score": hit.get("rerank_score"),
                        "traceability_status": hit.get("traceability_status"),
                    }
                    for hit in retrieval_hits[:MEL_MAX_EVIDENCE_PROMPT_HITS]
                ],
            },
            max_chars=1200,
        )

    indicators: list[Dict[str, Any]] = []
    if llm_mode and llm_available:
        prompts = getattr(strategy, "get_system_prompts", lambda: {})() or {}
        model_candidates = llm_model_candidates(
            str(getattr(config.llm, "mel_model", "") or ""),
            str(getattr(config.llm, "reasoning_model", "") or ""),
            str(getattr(config.llm, "cheap_model", "") or ""),
        )
        for model_name in model_candidates:
            llm_attempted = True
            llm_models_tried.append(model_name)
            raw_payload, llm_engine, llm_error = _llm_structured_mel(
                schema_cls=schema_cls,
                model_name=model_name,
                system_prompt=str(prompts.get("MEL_Specialist") or ""),
                donor_id=donor_id,
                project=project,
                country=country,
                input_context=input_context,
                toc_payload=toc_payload if isinstance(toc_payload, dict) else {},
                revision_hint=revision_hint,
                evidence_hits=retrieval_hits,
                schema_contract_hint=schema_contract_hint,
                retrieval_trace_hint=retrieval_trace_hint,
                validation_error_hint=None,
            )
            if raw_payload is not None:
                generation_engine = llm_engine or f"llm:{model_name}"
                try:
                    parsed = _model_validate(schema_cls, raw_payload)
                    indicators = _normalize_llm_indicators(
                        _extract_mel_indicators(_model_dump(parsed)),
                        namespace=namespace,
                        donor_id=donor_id,
                        input_context=input_context,
                    )
                except Exception as exc:
                    llm_repair_attempted = True
                    raw_payload_retry, llm_engine_retry, llm_error_retry = _llm_structured_mel(
                        schema_cls=schema_cls,
                        model_name=model_name,
                        system_prompt=str(prompts.get("MEL_Specialist") or ""),
                        donor_id=donor_id,
                        project=project,
                        country=country,
                        input_context=input_context,
                        toc_payload=toc_payload if isinstance(toc_payload, dict) else {},
                        revision_hint=revision_hint,
                        evidence_hits=retrieval_hits,
                        schema_contract_hint=schema_contract_hint,
                        retrieval_trace_hint=retrieval_trace_hint,
                        validation_error_hint=str(exc),
                    )
                    if raw_payload_retry is not None:
                        generation_engine = llm_engine_retry or generation_engine
                        try:
                            parsed_retry = _model_validate(schema_cls, raw_payload_retry)
                            indicators = _normalize_llm_indicators(
                                _extract_mel_indicators(_model_dump(parsed_retry)),
                                namespace=namespace,
                                donor_id=donor_id,
                                input_context=input_context,
                            )
                        except Exception as exc_retry:
                            llm_error = f"LLM MEL structured output validation failed after retry: {exc_retry}"
                            llm_failure_reasons.append(f"{model_name}: {llm_error}")
                        else:
                            llm_selected_model = model_name
                            if llm_error_retry:
                                llm_error = llm_error_retry
                            break
                    else:
                        llm_error = llm_error_retry or f"LLM MEL structured output validation failed: {exc}"
                        llm_failure_reasons.append(f"{model_name}: {llm_error}")
                else:
                    llm_selected_model = model_name
                    break
            else:
                llm_failure_reasons.append(f"{model_name}: {llm_error or 'structured_output_failed'}")
    elif llm_mode and not llm_available:
        llm_error = openai_compatible_missing_reason()
    if llm_mode and not indicators and llm_failure_reasons and not llm_error:
        llm_error = "; ".join(llm_failure_reasons[:3])

    if not indicators:
        deterministic_indicators = _deterministic_indicators_from_toc(
            toc_payload=toc_payload if isinstance(toc_payload, dict) else {},
            retrieval_hits=retrieval_hits,
            namespace=namespace,
            donor_id=donor_id,
            input_context=input_context,
            max_indicators=max(top_k, 2),
        )
        if deterministic_indicators:
            indicators = deterministic_indicators
            deterministic_source = "toc_results_template"
        elif retrieval_hits:
            indicators = [
                _indicator_from_hit(
                    hit,
                    idx=idx,
                    namespace=namespace,
                    donor_id=donor_id,
                    input_context=input_context,
                )
                for idx, hit in enumerate(retrieval_hits)
            ]
            deterministic_source = "retrieval_template"
        else:
            indicators = [_fallback_indicator(namespace, donor_id=donor_id, input_context=input_context)]
            deterministic_source = "fallback_single_indicator"
        if llm_mode:
            generation_engine = f"fallback:{deterministic_source}"
            fallback_used = True
            fallback_class = "emergency"
        else:
            generation_engine = f"deterministic:{deterministic_source}"
            fallback_class = "deterministic_mode"

    citation_records = _build_mel_citations(
        indicators=indicators,
        evidence_hits=retrieval_hits,
        namespace=namespace,
        namespace_normalized=namespace_normalized,
        donor_id=donor_id,
        use_strategy_reference_when_no_hits=(not llm_mode and not retrieval_hits),
    )
    mel_generation_meta: Dict[str, Any] = {
        "engine": generation_engine,
        "llm_used": generation_engine.startswith("llm:"),
        "llm_requested": llm_mode,
        "llm_available": llm_available,
        "llm_attempted": llm_attempted,
        "llm_attempt_count": len(llm_models_tried),
        "llm_models_tried": llm_models_tried,
        "llm_selected_model": llm_selected_model,
        "retrieval_used": bool(retrieval_hits),
        "fallback_used": fallback_used,
        "fallback_class": fallback_class,
        "schema_name": getattr(schema_cls, "__name__", "MELDraftOutput"),
        "schema_contract_hint_present": bool(schema_contract_hint),
        "input_context_key_count": len(input_context),
        "retrieval_prompt_hit_count": min(len(retrieval_hits), MEL_MAX_EVIDENCE_PROMPT_HITS),
        "retrieval_trace_hint_present": bool(retrieval_trace_hint),
        "max_prompt_evidence_hits": MEL_MAX_EVIDENCE_PROMPT_HITS,
        "deterministic_source": deterministic_source if not generation_engine.startswith("llm:") else None,
    }
    if llm_error:
        mel_generation_meta["llm_fallback_reason"] = llm_error
    if llm_failure_reasons:
        mel_generation_meta["llm_failure_reasons"] = llm_failure_reasons[:5]
    if llm_repair_attempted:
        mel_generation_meta["llm_validation_repair_attempted"] = True

    rag_trace["citation_count"] = len(citation_records)
    rag_trace["indicator_count"] = len(indicators)
    rag_trace["generation"] = mel_generation_meta
    mel = {"indicators": indicators, "rag_trace": rag_trace, "citations": citation_records}
    state["mel"] = mel
    state["logframe_draft"] = mel
    state["mel_generation_meta"] = mel_generation_meta
    append_draft_version(
        state,
        section="logframe",
        content=state["logframe_draft"],
        node="mel_specialist",
        iteration=state_iteration(state),
    )
    append_citations(state, citation_records)
    return state
