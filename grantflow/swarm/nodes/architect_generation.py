from __future__ import annotations

import json
import types
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import BaseModel

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.llm_provider import (
    chat_openai_init_kwargs,
    llm_model_candidates,
    openai_compatible_llm_available,
    openai_compatible_missing_reason,
)
from grantflow.swarm.nodes.architect_policy import (
    ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES,
    ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD,
    architect_claim_confidence_threshold,
    architect_donor_prompt_constraints,
    sanitize_validation_error_hint,
)
from grantflow.swarm.nodes.architect_retrieval import pick_best_architect_evidence_hit
from grantflow.swarm.state_contract import (
    normalize_state_contract,
    state_donor_id,
    state_input_context,
    state_llm_mode,
    state_rag_namespace,
    state_revision_hint,
)

ARCHITECT_PLACEHOLDER_TOKENS = {
    "",
    "tbd",
    "to be determined",
    "placeholder",
    "n/a",
    "na",
    "none",
    "unknown",
    "-",
    "--",
    "null",
}


def _model_validate(schema_cls: Type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    validator = getattr(schema_cls, "model_validate", None)
    if callable(validator):
        return validator(payload)
    return schema_cls.parse_obj(payload)


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    dumper = getattr(model, "model_dump", None)
    if callable(dumper):
        return dumper()
    return model.dict()


def _is_basemodel_subclass(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    union_type = getattr(types, "UnionType", None)
    allowed_origins = (Union, union_type) if union_type is not None else (Union,)
    if origin not in allowed_origins:
        return annotation
    args = [a for a in get_args(annotation) if a is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


def _short_evidence_hint(evidence_hits: Iterable[Dict[str, Any]]) -> str:
    for hit in evidence_hits:
        excerpt = str((hit or {}).get("excerpt") or "").strip()
        if excerpt:
            return excerpt[:120]
    return ""


def _safe_json(value: Any, *, max_chars: int = 1600) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        text = str(value)
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."


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


def _is_placeholder_text(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token in ARCHITECT_PLACEHOLDER_TOKENS


def _collect_soft_quality_issues(value: Any, path: str = "toc") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            issues.extend(_collect_soft_quality_issues(inner, f"{path}.{key}"))
        return issues
    if isinstance(value, list):
        for idx, inner in enumerate(value):
            issues.extend(_collect_soft_quality_issues(inner, f"{path}[{idx}]"))
        return issues
    if not isinstance(value, str):
        return issues

    text = str(value).strip()
    lowered_path = path.lower()
    if any(token in lowered_path for token in ("_id", ".id", "indicator_code", ".code")):
        return issues
    if _is_placeholder_text(text):
        issues.append(f"{path}:placeholder")
        return issues
    if any(token in lowered_path for token in ("goal", "objective", "outcome", "result", "description", "rationale")):
        if len(text) < 8:
            issues.append(f"{path}:too_short")
    return issues


def _soft_quality_issue_hint(issues: list[str], *, max_items: int = 6) -> str:
    if not issues:
        return ""
    sample = ", ".join(issues[:max_items])
    extra = f" (+{len(issues) - max_items} more)" if len(issues) > max_items else ""
    return f"Soft quality issues detected ({len(issues)}): {sample}{extra}. Replace placeholders with concrete text."


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


def _text_for_field(
    *,
    field_name: str,
    path: str,
    donor_id: str,
    project: str,
    country: str,
    revision_hint: str,
    evidence_hint: str,
    index: int = 0,
) -> str:
    lname = field_name.lower()
    base_project = project or "Project"
    suffix = f" {index + 1}" if index >= 0 else ""

    if lname.endswith("_id") or lname == "id":
        prefix = field_name.replace("_id", "").replace("_", " ").strip().title() or "Item"
        return f"{prefix} {index + 1}"
    if "indicator_code" in lname:
        return f"IND-{index + 1:03d}"
    if "country" in lname:
        return country or "TBD country"
    if "goal" in lname:
        return f"Improve {base_project} outcomes in {country or 'target locations'}."
    if "objective" in lname:
        return f"{base_project} objective{suffix} aligned with {donor_id} priorities."
    if "title" in lname:
        return f"{base_project} result{suffix}"
    if "description" in lname or "rationale" in lname or "expected_change" in lname:
        hint = f" Evidence hint: {evidence_hint}" if evidence_hint else ""
        return (
            f"{base_project} intervention delivers measurable change in {country or 'target context'} "
            f"through structured implementation and review cycles.{hint}"
        )[:420]
    if "assumption" in lname or "risk" in lname:
        if revision_hint:
            return f"Assumption {index + 1}: {revision_hint[:180]}"
        return f"Assumption {index + 1}: enabling conditions remain stable for implementation."
    if "stakeholder" in lname:
        return f"Stakeholder {index + 1}: implementing partner and relevant public institutions"
    if "partner_role" in lname:
        return "Local partner leads implementation outreach and routine monitoring coordination."
    if "line_of_effort" in lname:
        return "Governance and civic resilience"
    if "target" in lname:
        return "TBD target"
    if "justification" in lname:
        return f"Selected for logical alignment to {base_project} and donor reporting needs."
    if "citation" in lname:
        return donor_id
    if "brief" in lname:
        return f"ToC draft for {donor_id} - {base_project}"
    return f"{field_name.replace('_', ' ').capitalize()} for {base_project}{suffix}"


def _synthesize_value(
    annotation: Any,
    *,
    field_name: str,
    path: str,
    ctx: Dict[str, Any],
    evidence_hint: str,
    depth: int,
) -> Any:
    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)

    if annotation in (str,):
        return _text_for_field(
            field_name=field_name,
            path=path,
            donor_id=ctx["donor_id"],
            project=ctx["project"],
            country=ctx["country"],
            revision_hint=ctx["revision_hint"],
            evidence_hint=evidence_hint,
            index=max(0, int(ctx.get("index", 0) or 0)),
        )
    if annotation in (int,):
        return 1
    if annotation in (float,):
        return 1.0
    if annotation in (bool,):
        return True

    if _is_basemodel_subclass(annotation):
        return _synthesize_model(annotation, ctx=ctx, path=path, depth=depth + 1, evidence_hint=evidence_hint)

    if origin is list:
        args = get_args(annotation)
        inner = args[0] if args else str
        count = 2 if depth <= 1 else 1
        if any(k in field_name.lower() for k in ("assumption", "risk", "objective", "outcome", "output", "result")):
            count = 2
        items = []
        for i in range(count):
            subctx = dict(ctx)
            subctx["index"] = i
            items.append(
                _synthesize_value(
                    inner,
                    field_name=field_name.rstrip("s") or field_name,
                    path=f"{path}[{i}]",
                    ctx=subctx,
                    evidence_hint=evidence_hint,
                    depth=depth + 1,
                )
            )
        return items

    if origin is dict:
        return {}

    return _text_for_field(
        field_name=field_name,
        path=path,
        donor_id=ctx["donor_id"],
        project=ctx["project"],
        country=ctx["country"],
        revision_hint=ctx["revision_hint"],
        evidence_hint=evidence_hint,
        index=max(0, int(ctx.get("index", 0) or 0)),
    )


def _synthesize_model(
    schema_cls: Type[BaseModel],
    *,
    ctx: Dict[str, Any],
    path: str,
    depth: int,
    evidence_hint: str,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    fields = getattr(schema_cls, "model_fields", None)
    if not isinstance(fields, dict):  # pydantic v1 fallback
        fields = getattr(schema_cls, "__fields__", {})
    for field_name, field in fields.items():
        annotation = getattr(field, "annotation", None) or getattr(field, "outer_type_", None) or str
        data[field_name] = _synthesize_value(
            annotation,
            field_name=str(field_name),
            path=f"{path}.{field_name}" if path else str(field_name),
            ctx=ctx,
            evidence_hint=evidence_hint,
            depth=depth,
        )
    return data


def _fallback_structured_toc(
    schema_cls: Type[BaseModel],
    *,
    donor_id: str,
    project: str,
    country: str,
    revision_hint: str,
    evidence_hits: Iterable[Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    evidence_hint = _short_evidence_hint(evidence_hits)
    payload = _synthesize_model(
        schema_cls,
        ctx={
            "donor_id": donor_id,
            "project": project,
            "country": country,
            "revision_hint": revision_hint,
            "index": 0,
        },
        path="",
        depth=0,
        evidence_hint=evidence_hint,
    )
    return payload, "contract_synthesizer"


def _llm_structured_toc(
    schema_cls: Type[BaseModel],
    *,
    model_name: str,
    system_prompt: str,
    donor_id: str,
    project: str,
    country: str,
    input_context: Dict[str, Any],
    revision_hint: str,
    evidence_hits: Iterable[Dict[str, Any]],
    schema_contract_hint: str = "",
    validation_error_hint: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    llm_kwargs = chat_openai_init_kwargs(model=model_name, temperature=0.1)
    if llm_kwargs is None:
        return None, None, openai_compatible_missing_reason()

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        evidence_lines = []
        for hit in list(evidence_hits)[:3]:
            label = hit.get("label") or hit.get("source") or "evidence"
            page = hit.get("page")
            excerpt = str(hit.get("excerpt") or "").strip()
            page_hint = f" (page {page})" if page is not None else ""
            evidence_lines.append(f"- {label}{page_hint}: {excerpt[:220]}")

        human_prompt = (
            "Create a donor-aligned Theory of Change using the structured schema.\n\n"
            f"Donor: {donor_id}\n"
            f"Project: {project}\n"
            f"Country: {country}\n"
        )
        if input_context:
            human_prompt += f"Input context JSON: {_safe_json(input_context)}\n"
        if schema_contract_hint:
            human_prompt += "\nSchema contract (follow field names and types):\n"
            human_prompt += f"{schema_contract_hint}\n"
        if revision_hint:
            human_prompt += f"Revision instructions from critic: {revision_hint}\n"
        sanitized_validation_error_hint = sanitize_validation_error_hint(validation_error_hint)
        if sanitized_validation_error_hint:
            human_prompt += (
                "Previous structured output failed schema validation. "
                f"Repair the object and satisfy these validation errors: {sanitized_validation_error_hint}\n"
            )
        if evidence_lines:
            human_prompt += (
                "\nDonor guidance evidence (use as grounding cues, do not fabricate citations):\n"
                + "\n".join(evidence_lines)
                + "\n"
            )
        human_prompt += "\nDrafting constraints:\n"
        human_prompt += f"- {architect_donor_prompt_constraints(donor_id)}\n"
        human_prompt += "- Keep output concrete; avoid placeholders like TBD/placeholder.\n"
        human_prompt += "\nReturn the structured object only."

        llm = ChatOpenAI(**llm_kwargs)
        structured = llm.with_structured_output(schema_cls)
        result = structured.invoke(
            [
                SystemMessage(content=system_prompt or "Draft a compliant Theory of Change."),
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


def _extract_claim_strings(value: Any, path: str = "toc") -> list[tuple[str, str]]:
    claims: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            claims.extend(_extract_claim_strings(inner, f"{path}.{key}"))
        return claims
    if isinstance(value, list):
        for idx, inner in enumerate(value):
            claims.extend(_extract_claim_strings(inner, f"{path}[{idx}]"))
        return claims
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return claims
        lowered_path = path.lower()
        # Indicator-level fields are better grounded in MEL/logframe stage and create noisy
        # architect claim citations because ancestor path segments (e.g. intermediate_results)
        # can accidentally match generic "result" keywords.
        if ".indicators[" in lowered_path:
            return claims
        # Assumptions/risks are often design hypotheses rather than evidence-backed claims.
        # Treating them as architect claim citations inflates low-confidence noise.
        if ".critical_assumptions[" in lowered_path or ".assumptions[" in lowered_path or ".risks[" in lowered_path:
            return claims
        identifier_tokens = ("_id", ".id", "indicator_code", "code]")
        if any(token in lowered_path for token in identifier_tokens):
            return claims
        keywords = ("goal", "objective", "outcome", "result", "description", "assumption", "rationale", "change")
        if any(k in lowered_path for k in keywords):
            claims.append((path, text))
    return claims


def _claim_priority(statement_path: str) -> int:
    path = str(statement_path or "").lower()
    if path in {
        "toc.project_goal",
        "toc.project_development_objective",
        "toc.program_goal",
        "toc.programme_objective",
    }:
        return 5
    if any(token in path for token in (".development_objectives[", ".specific_objectives[", ".objectives[")):
        if any(path.endswith(suffix) for suffix in (".description", ".title", ".expected_change", ".objective")):
            return 5
        return 4
    if any(token in path for token in (".expected_outcomes[", ".results_chain[", ".outcomes[")):
        if any(path.endswith(suffix) for suffix in (".description", ".title", ".expected_change", ".indicator_focus")):
            return 4
        return 3
    if any(token in path for token in ("goal", "objective", "outcome", "result")):
        return 3
    if any(token in path for token in ("description", "rationale", "change")):
        return 2
    return 1


def extract_architect_claim_records(
    toc_payload: Dict[str, Any],
    *,
    max_claims: int = 24,
    max_high_priority_claims: int = 16,
) -> list[Dict[str, Any]]:
    raw_claims = _extract_claim_strings(toc_payload, "toc")
    deduped: list[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for statement_path, statement in raw_claims:
        clean_statement = " ".join(str(statement).split()).strip()
        if not clean_statement:
            continue
        dedupe_key = (str(statement_path).strip().lower(), clean_statement.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(
            {
                "statement_path": statement_path,
                "statement": clean_statement,
                "priority": _claim_priority(statement_path),
            }
        )
    deduped.sort(
        key=lambda row: (
            -int(row.get("priority") or 0),
            len(str(row.get("statement_path") or "")),
            str(row.get("statement_path") or ""),
        )
    )
    high_priority = [row for row in deduped if int(row.get("priority") or 0) >= 4][:max_high_priority_claims]
    remaining = max(0, max_claims - len(high_priority))
    normal_priority = [row for row in deduped if int(row.get("priority") or 0) < 4][:remaining]
    return high_priority + normal_priority


def summarize_architect_claim_citations(
    *,
    claim_records: list[Dict[str, Any]],
    citations: list[Dict[str, Any]],
) -> Dict[str, Any]:
    claim_paths = {
        str(row.get("statement_path") or "").strip()
        for row in claim_records
        if str(row.get("statement_path") or "").strip()
    }
    key_claim_paths = {
        str(row.get("statement_path") or "").strip()
        for row in claim_records
        if int(row.get("priority") or 0) >= 4 and str(row.get("statement_path") or "").strip()
    }
    claim_citations = [
        c
        for c in citations
        if isinstance(c, dict) and str(c.get("used_for") or "") == "toc_claim" and str(c.get("statement_path") or "")
    ]
    cited_paths = {str(c.get("statement_path") or "").strip() for c in claim_citations if c.get("statement_path")}
    confident_paths = {
        str(c.get("statement_path") or "").strip()
        for c in claim_citations
        if str(c.get("citation_type") or "") == "rag_claim_support"
    }
    fallback_claim_count = sum(1 for c in claim_citations if str(c.get("citation_type") or "") == "fallback_namespace")
    low_conf_claim_count = sum(1 for c in claim_citations if str(c.get("citation_type") or "") == "rag_low_confidence")
    traceability_complete_count = 0
    traceability_partial_count = 0
    traceability_missing_count = 0
    threshold_considered = 0
    threshold_hit_count = 0
    for citation in claim_citations:
        status = citation_traceability_status(citation)
        if status == "complete":
            traceability_complete_count += 1
        elif status == "partial":
            traceability_partial_count += 1
        else:
            traceability_missing_count += 1
        threshold_raw = citation.get("confidence_threshold")
        confidence_raw = citation.get("citation_confidence")
        try:
            threshold_value = float(threshold_raw) if threshold_raw is not None else None
            confidence_value = float(confidence_raw) if confidence_raw is not None else None
        except (TypeError, ValueError):
            threshold_value = None
            confidence_value = None
        if threshold_value is None or confidence_value is None:
            continue
        threshold_considered += 1
        if confidence_value >= threshold_value:
            threshold_hit_count += 1
    traceability_gap_count = traceability_partial_count + traceability_missing_count
    claim_citation_count = len(claim_citations)
    return {
        "claims_total": len(claim_records),
        "key_claims_total": len(key_claim_paths),
        "claim_citation_count": claim_citation_count,
        "claim_paths_covered": len(cited_paths & claim_paths),
        "key_claim_paths_covered": len(cited_paths & key_claim_paths),
        "confident_claim_paths_covered": len(confident_paths & claim_paths),
        "fallback_claim_count": fallback_claim_count,
        "low_confidence_claim_count": low_conf_claim_count,
        "traceability_complete_citation_count": traceability_complete_count,
        "traceability_partial_citation_count": traceability_partial_count,
        "traceability_missing_citation_count": traceability_missing_count,
        "traceability_gap_citation_count": traceability_gap_count,
        "threshold_considered_count": threshold_considered,
        "threshold_hit_count": threshold_hit_count,
        "claim_coverage_ratio": round((len(cited_paths & claim_paths) / len(claim_paths)), 4) if claim_paths else 1.0,
        "key_claim_coverage_ratio": (
            round((len(cited_paths & key_claim_paths) / len(key_claim_paths)), 4) if key_claim_paths else 1.0
        ),
        "fallback_claim_ratio": round((fallback_claim_count / claim_citation_count), 4) if claim_citation_count else 0.0,
        "traceability_gap_rate": (
            round((traceability_gap_count / claim_citation_count), 4) if claim_citation_count else 0.0
        ),
        "threshold_hit_rate": round((threshold_hit_count / threshold_considered), 4) if threshold_considered else None,
    }


def build_architect_claim_citations(
    *,
    toc_payload: Dict[str, Any],
    namespace: str,
    donor_id: str,
    evidence_hits: Iterable[Dict[str, Any]],
    retrieval_expected: bool = True,
) -> list[Dict[str, Any]]:
    hits = [h for h in evidence_hits if isinstance(h, dict)]
    namespace_normalized = vector_store.normalize_namespace(namespace)
    claims = extract_architect_claim_records(toc_payload)
    citations: list[Dict[str, Any]] = []

    if not claims:
        citations.append(
            {
                "stage": "architect",
                "citation_type": "strategy_namespace",
                "namespace": namespace,
                "namespace_normalized": namespace_normalized,
                "label": f"Based on {namespace}",
                "used_for": "toc_draft",
                "statement_path": "toc",
            }
        )
        return citations

    bounded_claims = claims
    if not hits:
        if not retrieval_expected:
            source_ref = f"strategy::{donor_id}"
            for row in bounded_claims:
                statement_path = str(row.get("statement_path") or "toc")
                statement = str(row.get("statement") or "").strip()
                if not statement:
                    continue
                priority = int(row.get("priority") or 1)
                synthetic_doc_id = f"strategy::{namespace_normalized}::{statement_path}"
                confidence_threshold = architect_claim_confidence_threshold(
                    donor_id=donor_id,
                    statement_path=statement_path,
                )
                citations.append(
                    {
                        "stage": "architect",
                        "citation_type": "strategy_reference",
                        "namespace": namespace,
                        "namespace_normalized": namespace_normalized,
                        "doc_id": synthetic_doc_id,
                        "chunk_id": synthetic_doc_id,
                        "source": source_ref,
                        "label": f"{namespace} strategy reference",
                        "used_for": "toc_claim",
                        "statement_path": statement_path,
                        "statement": statement[:240],
                        "statement_priority": priority,
                        "excerpt": statement[:240],
                        "citation_confidence": 0.75,
                        "raw_claim_confidence": 0.75,
                        "evidence_score": 0.75,
                        "retrieval_confidence": 0.75,
                        "confidence_threshold": confidence_threshold,
                        "traceability_status": "complete",
                        "traceability_complete": True,
                    }
                )
            if not citations:
                synthetic_doc_id = f"strategy::{namespace_normalized}::toc"
                citations.append(
                    {
                        "stage": "architect",
                        "citation_type": "strategy_reference",
                        "namespace": namespace,
                        "namespace_normalized": namespace_normalized,
                        "doc_id": synthetic_doc_id,
                        "chunk_id": synthetic_doc_id,
                        "source": source_ref,
                        "label": f"{namespace} strategy reference",
                        "used_for": "toc_claim",
                        "statement_path": "toc",
                        "statement": "ToC claims generated from donor strategy without retrieval.",
                        "citation_confidence": 0.75,
                        "raw_claim_confidence": 0.75,
                        "evidence_score": 0.75,
                        "retrieval_confidence": 0.75,
                        "confidence_threshold": architect_claim_confidence_threshold(donor_id=donor_id, statement_path="toc"),
                        "traceability_status": "complete",
                        "traceability_complete": True,
                    }
                )
            return citations

        for row in bounded_claims:
            statement_path = str(row.get("statement_path") or "toc")
            statement = str(row.get("statement") or "").strip()
            if not statement:
                continue
            priority = int(row.get("priority") or 1)
            citations.append(
                {
                    "stage": "architect",
                    "citation_type": "fallback_namespace",
                    "namespace": namespace,
                    "namespace_normalized": namespace_normalized,
                    "label": f"{namespace} (no retrieved evidence)",
                    "used_for": "toc_claim",
                    "statement_path": statement_path,
                    "statement": statement[:240],
                    "statement_priority": priority,
                    "citation_confidence": 0.1,
                    "raw_claim_confidence": 0.1,
                    "evidence_score": 0.1,
                    "retrieval_confidence": 0.1,
                    "confidence_threshold": architect_claim_confidence_threshold(
                        donor_id=donor_id,
                        statement_path=statement_path,
                    ),
                    "traceability_status": "missing",
                    "traceability_complete": False,
                }
            )
        if not citations:
            citations.append(
                {
                    "stage": "architect",
                    "citation_type": "fallback_namespace",
                    "namespace": namespace,
                    "namespace_normalized": namespace_normalized,
                    "label": f"{namespace} (no retrieved evidence)",
                    "used_for": "toc_claim",
                    "statement_path": "toc",
                    "statement": "ToC claims generated without retrieval evidence.",
                    "citation_confidence": 0.1,
                    "raw_claim_confidence": 0.1,
                    "evidence_score": 0.1,
                    "retrieval_confidence": 0.1,
                    "confidence_threshold": architect_claim_confidence_threshold(donor_id=donor_id, statement_path="toc"),
                    "traceability_status": "missing",
                    "traceability_complete": False,
                }
            )
        return citations

    for row in bounded_claims:
        statement_path = str(row.get("statement_path") or "toc")
        statement = str(row.get("statement") or "").strip()
        priority = int(row.get("priority") or 1)
        if not statement:
            continue
        hit: Dict[str, Any]
        raw_claim_confidence: float
        hit, raw_claim_confidence = pick_best_architect_evidence_hit(
            statement,
            hits,
            donor_id=donor_id,
            statement_path=statement_path,
        )
        retrieval_confidence = float(hit.get("retrieval_confidence") or 0.0) if hit else 0.0
        rerank_score = float(hit.get("rerank_score") or 0.0) if hit else 0.0
        confidence = round(
            max(
                raw_claim_confidence,
                min(
                    1.0,
                    (raw_claim_confidence * 0.7) + (retrieval_confidence * 0.2) + (rerank_score * 0.1),
                ),
            ),
            4,
        )
        traceability_status = citation_traceability_status(hit) if hit else "missing"
        confidence_threshold = architect_claim_confidence_threshold(donor_id=donor_id, statement_path=statement_path)
        if hit and traceability_status == "complete" and confidence >= confidence_threshold:
            citation_type = "rag_claim_support"
        elif hit:
            citation_type = "rag_low_confidence"
        else:
            citation_type = "fallback_namespace"
        citations.append(
            {
                "stage": "architect",
                "citation_type": citation_type,
                "namespace": namespace,
                "namespace_normalized": namespace_normalized,
                "doc_id": hit.get("doc_id"),
                "source": hit.get("source"),
                "page": hit.get("page"),
                "page_start": hit.get("page_start"),
                "page_end": hit.get("page_end"),
                "chunk": hit.get("chunk"),
                "chunk_id": hit.get("chunk_id"),
                "label": hit.get("label") or f"{namespace}",
                "used_for": "toc_claim",
                "statement_path": statement_path,
                "statement": statement[:240],
                "statement_priority": priority,
                "excerpt": str(hit.get("excerpt") or "")[:240] if hit else None,
                "citation_confidence": round(confidence if hit else 0.1, 4),
                "raw_claim_confidence": round(raw_claim_confidence if hit else 0.1, 4),
                "evidence_score": round(confidence if hit else 0.1, 4),
                "evidence_rank": hit.get("rank") if hit else None,
                "retrieval_rank": hit.get("retrieval_rank") if hit else None,
                "retrieval_confidence": hit.get("retrieval_confidence") if hit else 0.1,
                "retrieval_distance": hit.get("retrieval_distance") if hit else None,
                "confidence_threshold": confidence_threshold,
                "traceability_status": traceability_status,
                "traceability_complete": traceability_status == "complete",
            }
        )
    return citations


def generate_toc_under_contract(
    *,
    state: Dict[str, Any],
    strategy: Any,
    evidence_hits: Iterable[Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], list[Dict[str, Any]]]:
    normalize_state_contract(state)
    evidence_hits = [h for h in evidence_hits if isinstance(h, dict)]
    schema_cls = strategy.get_toc_schema()
    donor_id = state_donor_id(
        state,
        default=str(getattr(strategy, "donor_id", "donor")),
    )
    input_context = state_input_context(state)
    project = str(input_context.get("project") or "TBD project")
    country = str(input_context.get("country") or "TBD")
    revision_hint = state_revision_hint(state)
    schema_contract_hint = _schema_contract_hint(schema_cls)
    llm_mode = state_llm_mode(state, default=False)
    llm_available = openai_compatible_llm_available()
    llm_error: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    engine = "deterministic:contract_synthesizer"
    model: Optional[BaseModel] = None
    llm_repair_attempted = False
    llm_quality_repair_attempted = False
    llm_quality_issue_count = 0
    llm_quality_issue_sample: list[str] = []
    llm_attempted = False
    llm_selected_model: Optional[str] = None
    llm_models_tried: list[str] = []
    llm_failure_reasons: list[str] = []
    fallback_used = False
    fallback_class = "deterministic_mode"

    if llm_mode and llm_available:
        prompts = getattr(strategy, "get_system_prompts", lambda: {})() or {}
        model_candidates = llm_model_candidates(
            str(getattr(config.llm, "architect_model", "") or ""),
            str(getattr(config.llm, "reasoning_model", "") or ""),
            str(getattr(config.llm, "cheap_model", "") or ""),
        )
        for model_name in model_candidates:
            llm_attempted = True
            llm_models_tried.append(model_name)
            raw_payload, llm_engine, llm_error = _llm_structured_toc(
                schema_cls,
                model_name=model_name,
                system_prompt=str(prompts.get("Architect") or ""),
                donor_id=donor_id,
                project=project,
                country=country,
                input_context=input_context,
                revision_hint=revision_hint,
                evidence_hits=evidence_hits,
                schema_contract_hint=schema_contract_hint,
                validation_error_hint=None,
            )
            if raw_payload:
                engine = llm_engine or f"llm:{model_name}"
                try:
                    model = _model_validate(schema_cls, raw_payload)
                except Exception as exc:
                    llm_validation_error = str(exc)
                    llm_repair_attempted = True
                    raw_payload, llm_engine_retry, llm_error_retry = _llm_structured_toc(
                        schema_cls,
                        model_name=model_name,
                        system_prompt=str(prompts.get("Architect") or ""),
                        donor_id=donor_id,
                        project=project,
                        country=country,
                        input_context=input_context,
                        revision_hint=revision_hint,
                        evidence_hits=evidence_hits,
                        schema_contract_hint=schema_contract_hint,
                        validation_error_hint=llm_validation_error,
                    )
                    if raw_payload:
                        engine = llm_engine_retry or engine
                        try:
                            model = _model_validate(schema_cls, raw_payload)
                        except Exception as exc_retry:
                            llm_error = f"LLM structured output failed validation after retry: {exc_retry}"
                            llm_failure_reasons.append(f"{model_name}: {llm_error}")
                            raw_payload = None
                        else:
                            llm_selected_model = model_name
                            if llm_error_retry:
                                llm_error = llm_error_retry
                            break
                    else:
                        llm_error = llm_error_retry or f"LLM structured output failed validation: {llm_validation_error}"
                        llm_failure_reasons.append(f"{model_name}: {llm_error}")
                else:
                    soft_quality_issues = _collect_soft_quality_issues(raw_payload)
                    if soft_quality_issues:
                        llm_quality_repair_attempted = True
                        llm_quality_issue_count = len(soft_quality_issues)
                        llm_quality_issue_sample = soft_quality_issues[:6]
                        quality_hint = _soft_quality_issue_hint(soft_quality_issues)
                        raw_payload_retry, llm_engine_retry, llm_error_retry = _llm_structured_toc(
                            schema_cls,
                            model_name=model_name,
                            system_prompt=str(prompts.get("Architect") or ""),
                            donor_id=donor_id,
                            project=project,
                            country=country,
                            input_context=input_context,
                            revision_hint=revision_hint,
                            evidence_hits=evidence_hits,
                            schema_contract_hint=schema_contract_hint,
                            validation_error_hint=quality_hint,
                        )
                        if raw_payload_retry:
                            try:
                                model = _model_validate(schema_cls, raw_payload_retry)
                            except Exception as exc_retry:
                                llm_error = f"LLM quality-repair payload failed validation: {exc_retry}"
                                llm_failure_reasons.append(f"{model_name}: {llm_error}")
                                llm_selected_model = model_name
                                break
                            else:
                                raw_payload = raw_payload_retry
                                engine = llm_engine_retry or engine
                                llm_selected_model = model_name
                                if llm_error_retry:
                                    llm_error = llm_error_retry
                                break
                        elif llm_error_retry:
                            llm_error = llm_error_retry
                        llm_selected_model = model_name
                        break
                    llm_selected_model = model_name
                    break
            else:
                llm_failure_reasons.append(f"{model_name}: {llm_error or 'structured_output_failed'}")

        if model is None and llm_failure_reasons and not llm_error:
            llm_error = "; ".join(llm_failure_reasons[:3])
    elif llm_mode and not llm_available:
        llm_error = openai_compatible_missing_reason()

    if raw_payload is None:
        raw_payload, synth_engine = _fallback_structured_toc(
            schema_cls,
            donor_id=donor_id,
            project=project,
            country=country,
            revision_hint=revision_hint,
            evidence_hits=evidence_hits,
        )
        if llm_mode:
            engine = f"fallback:{synth_engine}"
            fallback_used = True
            fallback_class = "emergency"
        else:
            engine = f"deterministic:{synth_engine}"
            fallback_class = "deterministic_mode"
        model = None

    if model is None:
        model = _model_validate(schema_cls, raw_payload)
    toc_payload = _model_dump(model)
    namespace = state_rag_namespace(state, default=strategy.get_rag_collection())
    claim_records = extract_architect_claim_records(toc_payload)
    claim_citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace=namespace,
        donor_id=donor_id,
        evidence_hits=evidence_hits,
        retrieval_expected=bool(state.get("architect_rag_enabled", True)),
    )
    claim_citation_stats = summarize_architect_claim_citations(
        claim_records=claim_records,
        citations=claim_citations,
    )

    validation: Dict[str, Any] = {
        "valid": True,
        "schema_name": getattr(schema_cls, "__name__", "TOCSchema"),
        "error_count": 0,
        "errors": [],
    }
    generation_meta: Dict[str, Any] = {
        "engine": engine,
        "llm_used": engine.startswith("llm:"),
        "llm_requested": llm_mode,
        "llm_available": llm_available,
        "llm_attempted": llm_attempted,
        "llm_attempt_count": len(llm_models_tried),
        "llm_models_tried": llm_models_tried,
        "llm_selected_model": llm_selected_model,
        "retrieval_used": bool(evidence_hits),
        "fallback_used": fallback_used,
        "fallback_class": fallback_class,
        "architect_mode": "llm" if llm_mode else "deterministic",
        "schema_name": validation["schema_name"],
        "schema_contract_hint_present": bool(schema_contract_hint),
        "input_context_key_count": len(input_context),
        "claim_coverage": claim_citation_stats,
        "citation_policy": {
            "default_high_confidence_threshold": ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD,
            "threshold_mode": "donor_section",
            "donor_overrides": dict(sorted(ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES.items())),
            "low_confidence_type": "rag_low_confidence",
        },
    }
    if llm_error:
        generation_meta["llm_fallback_reason"] = llm_error
    if llm_failure_reasons:
        generation_meta["llm_failure_reasons"] = llm_failure_reasons[:5]
    if llm_repair_attempted:
        generation_meta["llm_validation_repair_attempted"] = True
    if llm_quality_repair_attempted:
        generation_meta["llm_quality_repair_attempted"] = True
        generation_meta["llm_quality_issue_count"] = llm_quality_issue_count
        generation_meta["llm_quality_issue_sample"] = llm_quality_issue_sample
    return toc_payload, validation, generation_meta, claim_citations
