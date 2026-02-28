# grantflow/swarm/nodes/mel_specialist.py

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional, Tuple

from pydantic import BaseModel, Field

from grantflow.core.config import config
from grantflow.memory_bank.vector_store import vector_store
from grantflow.swarm.citation_source import citation_label_from_metadata, citation_source_from_metadata
from grantflow.swarm.citations import append_citations
from grantflow.swarm.llm_provider import (
    chat_openai_init_kwargs,
    openai_compatible_llm_available,
    openai_compatible_missing_reason,
)
from grantflow.swarm.retrieval_query import build_stage_query_text
from grantflow.swarm.state_contract import normalize_state_contract, state_input_context
from grantflow.swarm.versioning import append_draft_version

MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD = 0.35
MEL_MAX_EVIDENCE_PROMPT_HITS = 3


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
    return schema_cls.parse_obj(payload)  # type: ignore[attr-defined]


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    dumper = getattr(model, "model_dump", None)
    if callable(dumper):
        return dumper()
    return model.dict()  # type: ignore[attr-defined]


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
    project = str(input_context.get("project") or "").strip()
    country = str(input_context.get("country") or "").strip()
    problem = str(input_context.get("problem") or "").strip()
    expected_change = str(input_context.get("expected_change") or "").strip()
    toc = state.get("toc_draft", {}) or {}
    toc_payload = (toc.get("toc") or {}) if isinstance(toc, dict) else {}
    toc_summary = json.dumps(toc_payload, ensure_ascii=True)[:220] if isinstance(toc_payload, dict) else ""

    candidates = [
        base_query.strip(),
        f"{project} {country} MEL indicators baseline target verification frequency".strip(),
        f"{project} {country} monitoring evaluation learning results framework assumptions".strip(),
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
            doc_id = meta.get("doc_id") or meta.get("chunk_id") or (ids[idx] if idx < len(ids) else None)
            source = citation_source_from_metadata(meta)
            excerpt = str(doc or "")[:240]
            retrieval_conf = _retrieval_confidence(distances[idx] if idx < len(distances) else None, idx)
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
                "indicator_id": meta.get("indicator_id"),
                "name": meta.get("name"),
                "baseline": meta.get("baseline"),
                "target": meta.get("target"),
                "source": source,
                "page": meta.get("page"),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
                "chunk": meta.get("chunk"),
                "chunk_id": meta.get("chunk_id") or doc_id,
                "label": citation_label_from_metadata(meta, namespace=namespace, rank=retrieval_rank),
                "excerpt": excerpt,
                "retrieval_confidence": retrieval_conf,
                "rerank_score": round(min(1.0, rerank_score), 4),
            }

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


def _hit_traceability_status(hit: Dict[str, Any]) -> str:
    doc_id = str(hit.get("doc_id") or hit.get("chunk_id") or "").strip()
    source = str(hit.get("source") or "").strip()
    page = hit.get("page")
    if doc_id and source:
        return "complete"
    if doc_id or source or page is not None:
        return "partial"
    return "missing"


def _indicator_from_hit(hit: Dict[str, Any], *, idx: int, namespace: str) -> Dict[str, Any]:
    return {
        "indicator_id": str(hit.get("indicator_id") or f"IND_{idx + 1:03d}"),
        "name": str(hit.get("name") or f"Indicator from {namespace} #{idx + 1}"),
        "justification": (
            "Selected from donor-specific RAG collection " f"'{namespace}' based on project and ToC relevance."
        ),
        "citation": str(hit.get("label") or namespace),
        "baseline": str(hit.get("baseline") or "TBD"),
        "target": str(hit.get("target") or "TBD"),
        "evidence_excerpt": str(hit.get("excerpt") or "")[:240],
    }


def _normalize_indicator_item(item: Any, *, idx: int, namespace: str) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    indicator_id = str(item.get("indicator_id") or f"IND_{idx + 1:03d}").strip() or f"IND_{idx + 1:03d}"
    name = str(item.get("name") or "").strip() or f"Indicator {idx + 1}"
    justification = str(item.get("justification") or "").strip() or "Indicator selected for MEL coverage."
    citation = str(item.get("citation") or "").strip() or namespace
    baseline = str(item.get("baseline") or "TBD").strip() or "TBD"
    target = str(item.get("target") or "TBD").strip() or "TBD"
    evidence_excerpt = str(item.get("evidence_excerpt") or "").strip() or None
    return {
        "indicator_id": indicator_id,
        "name": name,
        "justification": justification,
        "citation": citation,
        "baseline": baseline,
        "target": target,
        "evidence_excerpt": evidence_excerpt,
    }


def _fallback_indicator(namespace: str) -> Dict[str, Any]:
    return {
        "indicator_id": "IND_001",
        "name": "Project Output Indicator",
        "justification": "Fallback indicator used because donor-specific RAG retrieval returned no grounded results.",
        "citation": namespace,
        "baseline": "TBD",
        "target": "TBD",
        "evidence_excerpt": None,
    }


def _normalize_llm_indicators(
    raw_indicators: Any,
    *,
    namespace: str,
) -> list[Dict[str, Any]]:
    if not isinstance(raw_indicators, list):
        return []
    indicators: list[Dict[str, Any]] = []
    for idx, item in enumerate(raw_indicators):
        normalized = _normalize_indicator_item(item, idx=idx, namespace=namespace)
        if normalized is None:
            continue
        indicators.append(normalized)
    return indicators


def _llm_structured_mel(
    *,
    system_prompt: str,
    donor_id: str,
    project: str,
    country: str,
    toc_payload: Dict[str, Any],
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
            f"ToC summary: {toc_summary}\n"
        )
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
            "- Return structured object only.\n"
        )

        llm = ChatOpenAI(**llm_kwargs)
        structured = llm.with_structured_output(MELDraftOutput)
        result = structured.invoke(
            [
                SystemMessage(content=system_prompt or "You are a MEL specialist drafting indicator sets."),
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


def _build_mel_citations(
    *,
    indicators: list[Dict[str, Any]],
    evidence_hits: Iterable[Dict[str, Any]],
    namespace: str,
) -> list[Dict[str, Any]]:
    hits = [h for h in evidence_hits if isinstance(h, dict)]
    threshold = _bounded_float(
        getattr(config.rag, "mel_citation_high_confidence_threshold", MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD),
        default=MEL_CITATION_HIGH_CONFIDENCE_THRESHOLD,
        low=0.0,
        high=1.0,
    )
    citations: list[Dict[str, Any]] = []
    for idx, indicator in enumerate(indicators):
        indicator_id = str(indicator.get("indicator_id") or f"IND_{idx + 1:03d}")
        name = str(indicator.get("name") or "")
        justification = str(indicator.get("justification") or "")
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
        traceability_status = _hit_traceability_status(hit) if hit else "missing"
        if hit and traceability_status == "complete" and confidence >= threshold:
            citation_type = "rag_result"
        elif hit:
            citation_type = "rag_low_confidence"
        else:
            citation_type = "fallback_namespace"
        label = str(hit.get("label") or indicator.get("citation") or namespace)
        citations.append(
            {
                "stage": "mel",
                "citation_type": citation_type,
                "namespace": namespace,
                "doc_id": hit.get("doc_id"),
                "source": hit.get("source"),
                "page": hit.get("page"),
                "page_start": hit.get("page_start"),
                "page_end": hit.get("page_end"),
                "chunk": hit.get("chunk"),
                "chunk_id": hit.get("chunk_id") or hit.get("doc_id"),
                "label": label,
                "used_for": indicator_id,
                "statement": statement[:240] or None,
                "excerpt": str(hit.get("excerpt") or indicator.get("evidence_excerpt") or "")[:240] or None,
                "citation_confidence": round(confidence if hit else 0.1, 4),
                "evidence_score": round(confidence if hit else 0.1, 4),
                "evidence_rank": hit.get("rank"),
                "retrieval_rank": hit.get("retrieval_rank") or hit.get("rank"),
                "retrieval_confidence": hit.get("retrieval_confidence") if hit else 0.1,
                "confidence_threshold": threshold,
                "traceability_status": traceability_status,
                "traceability_complete": traceability_status == "complete",
            }
        )
    return citations


def mel_assign_indicators(state: Dict[str, Any]) -> Dict[str, Any]:
    """Назначает MEL индикаторы c RAG retrieval и optional LLM structured generation."""
    normalize_state_contract(state)
    strategy = state.get("donor_strategy") or state.get("strategy")
    if not strategy:
        state.setdefault("errors", []).append("MEL cannot run without donor_strategy")
        return state

    namespace = strategy.get_rag_collection()
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
    project = str(input_context.get("project") or "TBD project")
    country = str(input_context.get("country") or "TBD")
    toc = state.get("toc_draft", {}) or {}
    toc_payload = (toc.get("toc") or {}) if isinstance(toc, dict) else {}
    critic_notes = state.get("critic_notes")
    revision_hint = ""
    if isinstance(critic_notes, dict):
        revision_hint = str(critic_notes.get("revision_instructions") or "")
    elif isinstance(critic_notes, str):
        revision_hint = critic_notes

    retrieval_hits: list[Dict[str, Any]] = []
    rag_trace: Dict[str, Any] = {
        "namespace": namespace,
        "query": query_text,
        "query_variants": query_variants,
        "query_variants_count": len(query_variants),
        "top_k": top_k,
        "rerank_pool_size": rerank_pool_size,
        "min_hit_confidence": round(min_hit_confidence, 3),
        "used_results": 0,
    }
    llm_mode = bool(state.get("llm_mode", False))
    llm_available = openai_compatible_llm_available()
    llm_attempted = False
    llm_repair_attempted = False
    llm_error: Optional[str] = None
    generation_engine = "deterministic:retrieval_template"
    fallback_used = False
    fallback_class = "deterministic_mode"

    try:
        result = vector_store.query(namespace=namespace, query_texts=query_variants, n_results=rerank_pool_size)
        retrieval_hits, retrieval_diag = _collect_retrieval_hits(
            result if isinstance(result, dict) else {},
            namespace=namespace,
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
                    "rerank_score": hit.get("rerank_score"),
                }
                for hit in retrieval_hits
            ]
            rag_trace["avg_retrieval_confidence"] = round(
                sum(float(hit.get("retrieval_confidence") or 0.0) for hit in retrieval_hits) / len(retrieval_hits),
                4,
            )
    except Exception as exc:
        state.setdefault("errors", []).append(f"MEL RAG query failed: {exc}")
        rag_trace["error"] = str(exc)

    indicators: list[Dict[str, Any]] = []
    if llm_mode and llm_available:
        llm_attempted = True
        prompts = getattr(strategy, "get_system_prompts", lambda: {})() or {}
        raw_payload, llm_engine, llm_error = _llm_structured_mel(
            system_prompt=str(prompts.get("MEL_Specialist") or ""),
            donor_id=str(state.get("donor_id") or state.get("donor") or getattr(strategy, "donor_id", "donor")),
            project=project,
            country=country,
            toc_payload=toc_payload if isinstance(toc_payload, dict) else {},
            revision_hint=revision_hint,
            evidence_hits=retrieval_hits,
            validation_error_hint=None,
        )
        if raw_payload is not None:
            generation_engine = llm_engine or "llm:unknown"
            try:
                parsed = _model_validate(MELDraftOutput, raw_payload)
                indicators = _normalize_llm_indicators(_model_dump(parsed).get("indicators"), namespace=namespace)
            except Exception as exc:
                llm_repair_attempted = True
                raw_payload_retry, llm_engine_retry, llm_error_retry = _llm_structured_mel(
                    system_prompt=str(prompts.get("MEL_Specialist") or ""),
                    donor_id=str(state.get("donor_id") or state.get("donor") or getattr(strategy, "donor_id", "donor")),
                    project=project,
                    country=country,
                    toc_payload=toc_payload if isinstance(toc_payload, dict) else {},
                    revision_hint=revision_hint,
                    evidence_hits=retrieval_hits,
                    validation_error_hint=str(exc),
                )
                if raw_payload_retry is not None:
                    generation_engine = llm_engine_retry or generation_engine
                    try:
                        parsed_retry = _model_validate(MELDraftOutput, raw_payload_retry)
                        indicators = _normalize_llm_indicators(
                            _model_dump(parsed_retry).get("indicators"), namespace=namespace
                        )
                    except Exception as exc_retry:
                        llm_error = f"LLM MEL structured output validation failed after retry: {exc_retry}"
                    else:
                        if llm_error_retry:
                            llm_error = llm_error_retry
                else:
                    llm_error = llm_error_retry or f"LLM MEL structured output validation failed: {exc}"
    elif llm_mode and not llm_available:
        llm_error = openai_compatible_missing_reason()

    if not indicators:
        if retrieval_hits:
            indicators = [
                _indicator_from_hit(hit, idx=idx, namespace=namespace) for idx, hit in enumerate(retrieval_hits)
            ]
        else:
            indicators = [_fallback_indicator(namespace)]
        if llm_mode:
            generation_engine = "fallback:retrieval_template"
            fallback_used = True
            fallback_class = "emergency"
        else:
            generation_engine = "deterministic:retrieval_template"
            fallback_class = "deterministic_mode"

    citation_records = _build_mel_citations(
        indicators=indicators,
        evidence_hits=retrieval_hits,
        namespace=namespace,
    )
    mel_generation_meta: Dict[str, Any] = {
        "engine": generation_engine,
        "llm_used": generation_engine.startswith("llm:"),
        "llm_requested": llm_mode,
        "llm_available": llm_available,
        "llm_attempted": llm_attempted,
        "retrieval_used": bool(retrieval_hits),
        "fallback_used": fallback_used,
        "fallback_class": fallback_class,
        "max_prompt_evidence_hits": MEL_MAX_EVIDENCE_PROMPT_HITS,
    }
    if llm_error:
        mel_generation_meta["llm_fallback_reason"] = llm_error
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
        iteration=int(state.get("iteration", state.get("iteration_count", 0)) or 0),
    )
    append_citations(state, citation_records)
    return state
