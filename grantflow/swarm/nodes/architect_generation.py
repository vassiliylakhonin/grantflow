from __future__ import annotations

import types
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import BaseModel

from grantflow.core.config import config
from grantflow.swarm.llm_provider import chat_openai_init_kwargs, openai_compatible_missing_reason
from grantflow.swarm.nodes.architect_policy import (
    ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES,
    ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD,
    architect_claim_confidence_threshold,
    architect_donor_prompt_constraints,
    sanitize_validation_error_hint,
)
from grantflow.swarm.nodes.architect_retrieval import pick_best_architect_evidence_hit
from grantflow.swarm.state_contract import normalize_state_contract, state_donor_id, state_input_context


def _model_validate(schema_cls: Type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    validator = getattr(schema_cls, "model_validate", None)
    if callable(validator):
        return validator(payload)
    return schema_cls.parse_obj(payload)  # type: ignore[attr-defined]


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    dumper = getattr(model, "model_dump", None)
    if callable(dumper):
        return dumper()
    return model.dict()  # type: ignore[attr-defined]


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
    ctx: Dict[str, str],
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
            index=max(0, ctx.get("index", 0)),  # type: ignore[arg-type]
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
        index=max(0, ctx.get("index", 0)),  # type: ignore[arg-type]
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
        fields = getattr(schema_cls, "__fields__", {})  # type: ignore[assignment]
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
    return payload, "fallback:contract_synthesizer"


def _llm_structured_toc(
    schema_cls: Type[BaseModel],
    *,
    system_prompt: str,
    donor_id: str,
    project: str,
    country: str,
    revision_hint: str,
    evidence_hits: Iterable[Dict[str, Any]],
    validation_error_hint: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    llm_kwargs = chat_openai_init_kwargs(model=config.llm.reasoning_model, temperature=0.1)
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
            return _model_dump(result), f"llm:{config.llm.reasoning_model}", None
        if isinstance(result, dict):
            return result, f"llm:{config.llm.reasoning_model}", None
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
        if ".critical_assumptions[" in lowered_path or ".risks[" in lowered_path:
            return claims
        identifier_tokens = ("_id", ".id", "indicator_code", "code]")
        if any(token in lowered_path for token in identifier_tokens):
            return claims
        keywords = ("goal", "objective", "outcome", "result", "description", "assumption", "rationale", "change")
        if any(k in lowered_path for k in keywords):
            claims.append((path, text))
    return claims


def build_architect_claim_citations(
    *,
    toc_payload: Dict[str, Any],
    namespace: str,
    donor_id: str,
    evidence_hits: Iterable[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    hits = [h for h in evidence_hits if isinstance(h, dict)]
    claims = _extract_claim_strings(toc_payload, "toc")
    citations: list[Dict[str, Any]] = []

    if not claims:
        citations.append(
            {
                "stage": "architect",
                "citation_type": "strategy_namespace",
                "namespace": namespace,
                "label": f"Based on {namespace}",
                "used_for": "toc_draft",
                "statement_path": "toc",
            }
        )
        return citations

    for idx, (statement_path, statement) in enumerate(claims[:24]):
        hit: Dict[str, Any]
        confidence: float
        if hits:
            hit, confidence = pick_best_architect_evidence_hit(
                statement,
                hits,
                donor_id=donor_id,
                statement_path=statement_path,
            )
        else:
            hit, confidence = {}, 0.0
        confidence_threshold = architect_claim_confidence_threshold(donor_id=donor_id, statement_path=statement_path)
        if hit and confidence >= confidence_threshold:
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
                "excerpt": str(hit.get("excerpt") or "")[:240] if hit else None,
                "citation_confidence": round(confidence if hit else 0.1, 4),
                "evidence_score": round(confidence if hit else 0.1, 4),
                "evidence_rank": hit.get("rank") if hit else None,
                "retrieval_rank": hit.get("retrieval_rank") if hit else None,
                "retrieval_confidence": hit.get("retrieval_confidence") if hit else 0.1,
                "confidence_threshold": confidence_threshold,
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
    critic_notes = state.get("critic_notes")
    revision_hint = ""
    if isinstance(critic_notes, dict):
        revision_hint = str(critic_notes.get("revision_instructions") or "")
    elif isinstance(critic_notes, str):
        revision_hint = critic_notes

    llm_mode = bool(state.get("llm_mode", False))
    llm_error: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    engine = "fallback:contract_synthesizer"
    model: Optional[BaseModel] = None
    llm_repair_attempted = False

    if llm_mode:
        prompts = getattr(strategy, "get_system_prompts", lambda: {})() or {}
        raw_payload, llm_engine, llm_error = _llm_structured_toc(
            schema_cls,
            system_prompt=str(prompts.get("Architect") or ""),
            donor_id=donor_id,
            project=project,
            country=country,
            revision_hint=revision_hint,
            evidence_hits=evidence_hits,
            validation_error_hint=None,
        )
        if raw_payload:
            engine = llm_engine or engine
            try:
                model = _model_validate(schema_cls, raw_payload)
            except Exception as exc:
                llm_validation_error = str(exc)
                llm_repair_attempted = True
                raw_payload, llm_engine_retry, llm_error_retry = _llm_structured_toc(
                    schema_cls,
                    system_prompt=str(prompts.get("Architect") or ""),
                    donor_id=donor_id,
                    project=project,
                    country=country,
                    revision_hint=revision_hint,
                    evidence_hits=evidence_hits,
                    validation_error_hint=llm_validation_error,
                )
                if raw_payload:
                    engine = llm_engine_retry or engine
                    try:
                        model = _model_validate(schema_cls, raw_payload)
                    except Exception as exc_retry:
                        llm_error = f"LLM structured output failed validation after retry: {exc_retry}"
                        raw_payload = None
                    else:
                        if llm_error_retry:
                            llm_error = llm_error_retry
                else:
                    llm_error = llm_error_retry or f"LLM structured output failed validation: {llm_validation_error}"

    if raw_payload is None:
        raw_payload, engine = _fallback_structured_toc(
            schema_cls,
            donor_id=donor_id,
            project=project,
            country=country,
            revision_hint=revision_hint,
            evidence_hits=evidence_hits,
        )
        model = None

    if model is None:
        model = _model_validate(schema_cls, raw_payload)
    toc_payload = _model_dump(model)
    namespace = strategy.get_rag_collection()
    claim_citations = build_architect_claim_citations(
        toc_payload=toc_payload,
        namespace=namespace,
        donor_id=donor_id,
        evidence_hits=evidence_hits,
    )

    validation = {
        "valid": True,
        "schema_name": getattr(schema_cls, "__name__", "TOCSchema"),
        "error_count": 0,
        "errors": [],
    }
    generation_meta: Dict[str, Any] = {
        "engine": engine,
        "llm_used": engine.startswith("llm:"),
        "retrieval_used": bool(evidence_hits),
        "schema_name": validation["schema_name"],
        "citation_policy": {
            "default_high_confidence_threshold": ARCHITECT_CITATION_HIGH_CONFIDENCE_THRESHOLD,
            "threshold_mode": "donor_section",
            "donor_overrides": dict(sorted(ARCHITECT_CITATION_DONOR_THRESHOLD_OVERRIDES.items())),
            "low_confidence_type": "rag_low_confidence",
        },
    }
    if llm_error:
        generation_meta["llm_fallback_reason"] = llm_error
    if llm_repair_attempted:
        generation_meta["llm_validation_repair_attempted"] = True
    return toc_payload, validation, generation_meta, claim_citations
