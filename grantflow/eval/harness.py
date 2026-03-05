from __future__ import annotations

import argparse
import json
import random
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from grantflow.core.config import config
from grantflow.core.strategies.factory import DonorFactory
from grantflow.eval.sample_presets import available_sample_ids, load_sample_eval_cases
from grantflow.swarm.citations import (
    citation_has_doc_id,
    citation_has_retrieval_confidence,
    citation_has_retrieval_metadata,
    citation_has_retrieval_rank,
    citation_traceability_status,
    is_fallback_namespace_citation_type,
    is_non_retrieval_citation_type,
    is_retrieval_grounded_citation_type,
    is_strategy_reference_citation_type,
)
from grantflow.swarm.findings import state_critic_findings
from grantflow.swarm.graph import grantflow_graph
from grantflow.swarm.state_contract import build_graph_state

FIXTURES_DIR = Path(__file__).with_name("fixtures")
DEFAULT_BASELINE_PATH = FIXTURES_DIR / "baseline_regression_snapshot.json"

HIGHER_IS_BETTER_METRICS = (
    "quality_score",
    "critic_score",
    "citations_total",
    "architect_citation_count",
    "architect_claim_citation_count",
    "mel_citation_count",
    "high_confidence_citation_count",
    "architect_threshold_hit_rate",
    "architect_key_claim_coverage_ratio",
    "draft_version_count",
    "citation_confidence_avg",
)
LOWER_IS_BETTER_METRICS = (
    "fatal_flaw_count",
    "high_severity_fatal_flaw_count",
    "error_count",
    "low_confidence_citation_count",
    "rag_low_confidence_citation_count",
    "fallback_namespace_citation_count",
    "non_retrieval_citation_rate",
    "traceability_gap_citation_rate",
    "architect_fallback_claim_ratio",
    "traceability_gap_citation_count",
    "traceability_partial_citation_count",
    "traceability_missing_citation_count",
)
BOOLEAN_GUARDRAIL_METRICS = (
    "toc_schema_valid",
    "has_toc_draft",
    "has_logframe_draft",
)
REGRESSION_TOLERANCE = 1e-6
REGRESSION_PRIORITY_WEIGHTS: dict[str, int] = {
    "toc_schema_valid": 5,
    "has_toc_draft": 5,
    "has_logframe_draft": 5,
    "error_count": 5,
    "high_severity_fatal_flaw_count": 5,
    "needs_revision": 4,
    "architect_threshold_hit_rate": 4,
    "architect_key_claim_coverage_ratio": 4,
    "citation_confidence_avg": 3,
    "fatal_flaw_count": 3,
    "quality_score": 2,
    "critic_score": 2,
    "low_confidence_citation_count": 2,
    "rag_low_confidence_citation_count": 2,
    "fallback_namespace_citation_count": 1,
    "non_retrieval_citation_rate": 2,
    "traceability_gap_citation_rate": 3,
    "architect_fallback_claim_ratio": 3,
}
GROUNDING_RISK_MIN_CITATIONS = 5
FALLBACK_DOMINANCE_WARN_RATIO = 0.6
FALLBACK_DOMINANCE_HIGH_RATIO = 0.85
NON_RETRIEVAL_DOMINANCE_WARN_RATIO = 0.6
NON_RETRIEVAL_DOMINANCE_HIGH_RATIO = 0.85
TRACEABILITY_GAP_WARN_RATIO = 0.4
TRACEABILITY_GAP_HIGH_RATIO = 0.7


def _dict_from(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_from(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fallback_dominance_label(*, fallback_count: int, citation_count: int) -> tuple[str | None, float | None]:
    if citation_count < GROUNDING_RISK_MIN_CITATIONS or citation_count <= 0:
        return None, None
    ratio = fallback_count / citation_count
    if ratio >= FALLBACK_DOMINANCE_HIGH_RATIO:
        return "high", round(ratio, 4)
    if ratio >= FALLBACK_DOMINANCE_WARN_RATIO:
        return "warn", round(ratio, 4)
    return None, round(ratio, 4)


def _non_retrieval_dominance_label(*, non_retrieval_count: int, citation_count: int) -> tuple[str | None, float | None]:
    if citation_count < GROUNDING_RISK_MIN_CITATIONS or citation_count <= 0:
        return None, None
    ratio = non_retrieval_count / citation_count
    if ratio >= NON_RETRIEVAL_DOMINANCE_HIGH_RATIO:
        return "high", round(ratio, 4)
    if ratio >= NON_RETRIEVAL_DOMINANCE_WARN_RATIO:
        return "warn", round(ratio, 4)
    return None, round(ratio, 4)


def _traceability_gap_label(*, gap_count: int, citation_count: int) -> tuple[str | None, float | None]:
    if citation_count < GROUNDING_RISK_MIN_CITATIONS or citation_count <= 0:
        return None, None
    ratio = gap_count / citation_count
    if ratio >= TRACEABILITY_GAP_HIGH_RATIO:
        return "high", round(ratio, 4)
    if ratio >= TRACEABILITY_GAP_WARN_RATIO:
        return "warn", round(ratio, 4)
    return None, round(ratio, 4)


def _looks_like_eval_case(item: Any) -> bool:
    return isinstance(item, dict) and ("donor_id" in item or "case_id" in item)


def load_eval_cases(
    fixtures_dir: Path | None = None,
    *,
    case_files: list[Path] | None = None,
) -> list[dict[str, Any]]:
    if case_files:
        source_files = [Path(path) for path in case_files]
    else:
        base_dir = fixtures_dir or FIXTURES_DIR
        source_files = sorted(base_dir.glob("*.json"))
    cases: list[dict[str, Any]] = []
    for path in source_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for item in payload:
                if _looks_like_eval_case(item):
                    item = dict(item)
                    item.setdefault("_fixture_file", path.name)
                    cases.append(item)
            continue
        if _looks_like_eval_case(payload):
            payload = dict(payload)
            payload.setdefault("_fixture_file", path.name)
            cases.append(payload)
    return cases


def apply_runtime_overrides_to_cases(
    cases: list[dict[str, Any]],
    *,
    force_llm: bool = False,
    force_architect_rag: bool = False,
    force_no_architect_rag: bool = False,
) -> list[dict[str, Any]]:
    if not (force_llm or force_architect_rag or force_no_architect_rag):
        return cases
    overridden: list[dict[str, Any]] = []
    for case in cases:
        next_case = dict(case)
        if force_llm:
            next_case["llm_mode"] = True
        if force_architect_rag:
            next_case["architect_rag_enabled"] = True
        if force_no_architect_rag:
            next_case["architect_rag_enabled"] = False
        overridden.append(next_case)
    return overridden


def filter_eval_cases(
    cases: list[dict[str, Any]],
    *,
    donor_ids: list[str] | None = None,
    case_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    donor_set = {str(v).strip().lower() for v in (donor_ids or []) if str(v).strip()}
    case_set = {str(v).strip() for v in (case_ids or []) if str(v).strip()}
    if not donor_set and not case_set:
        return cases

    filtered: list[dict[str, Any]] = []
    for case in cases:
        donor_id = str(case.get("donor_id") or "").strip().lower()
        case_id = str(case.get("case_id") or "").strip()
        if donor_set and donor_id not in donor_set:
            continue
        if case_set and case_id not in case_set:
            continue
        filtered.append(case)
    return filtered


def limit_eval_cases(
    cases: list[dict[str, Any]],
    *,
    max_cases: int | None = None,
    sample_seed: int | None = None,
) -> list[dict[str, Any]]:
    if max_cases is None:
        return cases
    max_items = int(max_cases)
    if max_items <= 0 or max_items >= len(cases):
        return cases
    if sample_seed is None:
        return cases[:max_items]
    rng = random.Random(int(sample_seed))
    selected_indices = set(rng.sample(range(len(cases)), max_items))
    return [case for idx, case in enumerate(cases) if idx in selected_indices]


def _split_csv_args(values: list[str] | None) -> list[str]:
    tokens: list[str] = []
    for raw in values or []:
        for part in str(raw or "").split(","):
            token = part.strip()
            if token:
                tokens.append(token)
    return tokens


def _resolve_manifest_entry_path(manifest_path: Path, file_value: Any) -> Path:
    raw = str(file_value or "").strip()
    if not raw:
        raise ValueError("Manifest row is missing file path")
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate
    manifest_relative = manifest_path.parent / candidate
    if manifest_relative.exists():
        return manifest_relative
    return cwd_candidate


def seed_rag_corpus_from_manifest(
    manifest_path: Path,
    *,
    allowed_donor_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    from grantflow.memory_bank.ingest import ingest_pdf_to_namespace

    donor_filter = {str(item).strip().lower() for item in (allowed_donor_ids or []) if str(item).strip()}
    lines = [line.strip() for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seeded_total = 0
    skipped_total = 0
    errors: list[str] = []
    donor_counts: dict[str, int] = {}
    donor_namespaces: dict[str, str] = {}
    donor_doc_family_counts: dict[str, dict[str, int]] = {}
    for idx, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except Exception as exc:
            errors.append(f"line {idx}: invalid json ({exc})")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {idx}: row must be object")
            continue
        donor_id = str(row.get("donor_id") or "").strip().lower()
        if not donor_id:
            errors.append(f"line {idx}: donor_id is missing")
            continue
        if donor_filter and donor_id not in donor_filter:
            skipped_total += 1
            continue
        try:
            strategy = DonorFactory.get_strategy(donor_id)
        except Exception as exc:
            errors.append(f"line {idx}: unknown donor_id '{donor_id}' ({exc})")
            continue
        namespace = str(strategy.get_rag_collection() or "").strip() or donor_id
        donor_namespaces[donor_id] = namespace
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        doc_family = str(metadata.get("doc_family") or "").strip().lower()
        try:
            file_path = _resolve_manifest_entry_path(manifest_path, row.get("file"))
            if not file_path.exists():
                errors.append(f"line {idx}: file not found ({file_path})")
                continue
            ingest_pdf_to_namespace(str(file_path), namespace=namespace, metadata=metadata)
            seeded_total += 1
            donor_counts[donor_id] = int(donor_counts.get(donor_id) or 0) + 1
            if doc_family:
                donor_family_counts = donor_doc_family_counts.setdefault(donor_id, {})
                donor_family_counts[doc_family] = int(donor_family_counts.get(doc_family) or 0) + 1
        except Exception as exc:
            errors.append(f"line {idx}: ingest failed ({exc})")
    return {
        "manifest_path": str(manifest_path),
        "seeded_total": seeded_total,
        "skipped_total": skipped_total,
        "errors": errors,
        "donor_counts": donor_counts,
        "donor_namespaces": donor_namespaces,
        "donor_doc_family_counts": donor_doc_family_counts,
    }


def expected_doc_families_by_donor(cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {}
    for case in cases:
        donor_id = str(case.get("donor_id") or "").strip().lower()
        if not donor_id:
            continue
        raw_expected = case.get("expected_doc_families")
        rows = raw_expected if isinstance(raw_expected, list) else []
        if not rows:
            continue
        donor_rows = expected.setdefault(donor_id, [])
        seen = {str(item).strip().lower() for item in donor_rows}
        for item in rows:
            token = str(item or "").strip().lower()
            if not token or token in seen:
                continue
            donor_rows.append(token)
            seen.add(token)
    return expected


def evaluate_seed_readiness(
    *,
    seeded_summary: dict[str, Any],
    expected_doc_families: dict[str, list[str]],
    min_uploads_per_family: int = 1,
) -> dict[str, Any]:
    min_uploads = max(1, int(min_uploads_per_family))
    donor_family_counts_raw = seeded_summary.get("donor_doc_family_counts")
    donor_family_counts = donor_family_counts_raw if isinstance(donor_family_counts_raw, dict) else {}

    donor_rows: dict[str, dict[str, Any]] = {}
    ready_donor_count = 0
    for donor_id, expected_families in expected_doc_families.items():
        expected_rows = [str(item).strip().lower() for item in (expected_families or []) if str(item).strip()]
        counts_raw = donor_family_counts.get(donor_id)
        counts = counts_raw if isinstance(counts_raw, dict) else {}
        family_counts: dict[str, int] = {}
        missing: list[str] = []
        underfilled: list[str] = []
        ready: list[str] = []
        for family in expected_rows:
            count = _to_int(counts.get(family), default=0)
            family_counts[family] = count
            if count <= 0:
                missing.append(family)
            elif count < min_uploads:
                underfilled.append(family)
            else:
                ready.append(family)
        donor_ready = not missing and not underfilled
        if donor_ready:
            ready_donor_count += 1
        donor_rows[donor_id] = {
            "ready": donor_ready,
            "expected_doc_families": expected_rows,
            "ready_doc_families": ready,
            "missing_doc_families": missing,
            "underfilled_doc_families": underfilled,
            "family_counts": family_counts,
            "coverage_rate": (round(len(ready) / len(expected_rows), 4) if expected_rows else None),
        }

    expected_donor_count = len(donor_rows)
    all_ready = expected_donor_count == 0 or ready_donor_count == expected_donor_count
    return {
        "enabled": expected_donor_count > 0,
        "all_ready": all_ready,
        "expected_donor_count": expected_donor_count,
        "ready_donor_count": ready_donor_count,
        "min_uploads_per_family": min_uploads,
        "donors": donor_rows,
    }


def build_initial_state(case: dict[str, Any]) -> dict[str, Any]:
    donor_id = str(case.get("donor_id") or "").strip()
    if not donor_id:
        raise ValueError(f"Missing donor_id in eval case: {case.get('case_id') or '<unknown>'}")
    strategy = DonorFactory.get_strategy(donor_id)

    input_payload = deepcopy(case.get("input_context") or {})
    if not isinstance(input_payload, dict):
        raise ValueError("input_context must be an object")

    return build_graph_state(
        donor_id=donor_id,
        input_context=input_payload,
        donor_strategy=strategy,
        llm_mode=bool(case.get("llm_mode", False)),
        max_iterations=int(case.get("max_iterations", config.graph.max_iterations)),
        extras={
            "architect_rag_enabled": bool(case.get("architect_rag_enabled", False)),
            "critic_notes": {},
        },
    )


def _count_stage_citations(citations: list[Any], stage: str) -> int:
    return sum(1 for c in citations if isinstance(c, dict) and c.get("stage") == stage)


def compute_state_metrics(state: dict[str, Any]) -> dict[str, Any]:
    citations = _list_from(state.get("citations"))
    draft_versions = _list_from(state.get("draft_versions"))
    errors = _list_from(state.get("errors"))
    critic_notes = _dict_from(state.get("critic_notes"))
    fatal_flaws = state_critic_findings(state, default_source="rules")
    toc_validation = _dict_from(state.get("toc_validation"))
    toc_generation_meta = _dict_from(state.get("toc_generation_meta"))
    claim_coverage_meta = _dict_from(toc_generation_meta.get("claim_coverage"))

    high_flaws = sum(
        1 for flaw in fatal_flaws if isinstance(flaw, dict) and str(flaw.get("severity") or "").lower() == "high"
    )
    llm_finding_label_counts: dict[str, int] = {}
    llm_advisory_applied_label_counts: dict[str, int] = {}
    llm_advisory_rejected_label_counts: dict[str, int] = {}
    for flaw in fatal_flaws:
        if not isinstance(flaw, dict):
            continue
        if str(flaw.get("source") or "").lower() != "llm":
            continue
        label = str(flaw.get("label") or "").strip() or "GENERIC_LLM_REVIEW_FLAG"
        llm_finding_label_counts[label] = int(llm_finding_label_counts.get(label, 0)) + 1
    llm_advisory_diagnostics = _dict_from(critic_notes.get("llm_advisory_diagnostics"))
    if llm_advisory_diagnostics:
        candidate_label_counts = _dict_from(llm_advisory_diagnostics.get("candidate_label_counts"))
        target_map = (
            llm_advisory_applied_label_counts
            if bool(llm_advisory_diagnostics.get("advisory_applies"))
            else llm_advisory_rejected_label_counts
        )
        for label, count in candidate_label_counts.items():
            label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
            try:
                inc = int(count or 0)
            except (TypeError, ValueError):
                inc = 0
            if inc <= 0:
                continue
            target_map[label_key] = int(target_map.get(label_key, 0)) + inc
    confidence_values: list[float] = []
    low_confidence_count = 0
    high_confidence_count = 0
    rag_low_confidence_count = 0
    fallback_namespace_count = 0
    strategy_reference_count = 0
    retrieval_grounded_count = 0
    non_retrieval_count = 0
    doc_id_present_count = 0
    retrieval_rank_present_count = 0
    retrieval_confidence_present_count = 0
    retrieval_metadata_complete_count = 0
    traceability_complete_count = 0
    traceability_partial_count = 0
    traceability_missing_count = 0
    architect_threshold_considered = 0
    architect_threshold_hits = 0
    architect_claim_citation_count = 0
    architect_claim_fallback_count = 0
    architect_claim_paths: set[str] = set()
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        if str(citation.get("stage") or "") == "architect":
            if str(citation.get("used_for") or "") == "toc_claim":
                architect_claim_citation_count += 1
                statement_path = str(citation.get("statement_path") or "").strip()
                if statement_path and statement_path != "toc":
                    architect_claim_paths.add(statement_path)
                if is_fallback_namespace_citation_type(citation.get("citation_type")):
                    architect_claim_fallback_count += 1
            threshold = citation.get("confidence_threshold")
            try:
                threshold_value = float(threshold) if threshold is not None else None
            except (TypeError, ValueError):
                threshold_value = None
            if threshold_value is not None:
                architect_threshold_considered += 1
                try:
                    conf_for_threshold = float(citation.get("citation_confidence") or 0.0)
                except (TypeError, ValueError):
                    conf_for_threshold = 0.0
                if conf_for_threshold >= threshold_value:
                    architect_threshold_hits += 1
        citation_type = citation.get("citation_type")
        if str(citation_type or "") == "rag_low_confidence":
            rag_low_confidence_count += 1
        if is_fallback_namespace_citation_type(citation_type):
            fallback_namespace_count += 1
        if is_strategy_reference_citation_type(citation_type):
            strategy_reference_count += 1
        if is_retrieval_grounded_citation_type(citation_type):
            retrieval_grounded_count += 1
        if is_non_retrieval_citation_type(citation_type):
            non_retrieval_count += 1
        if citation_has_doc_id(citation):
            doc_id_present_count += 1
        if citation_has_retrieval_rank(citation):
            retrieval_rank_present_count += 1
        if citation_has_retrieval_confidence(citation):
            retrieval_confidence_present_count += 1
        if citation_has_retrieval_metadata(citation):
            retrieval_metadata_complete_count += 1
        traceability_status = citation_traceability_status(citation)
        if traceability_status == "complete":
            traceability_complete_count += 1
        elif traceability_status == "partial":
            traceability_partial_count += 1
        else:
            traceability_missing_count += 1
        confidence = citation.get("citation_confidence")
        if confidence is None:
            continue
        try:
            conf_value = float(confidence)
        except (TypeError, ValueError):
            continue
        confidence_values.append(conf_value)
        if conf_value < 0.3:
            low_confidence_count += 1
        if conf_value >= 0.7:
            high_confidence_count += 1
    key_claim_coverage_ratio = _to_float(claim_coverage_meta.get("key_claim_coverage_ratio"), default=0.0)
    if key_claim_coverage_ratio <= 0.0 and architect_claim_paths:
        key_claim_total = _to_int(claim_coverage_meta.get("key_claims_total"), default=0)
        if key_claim_total <= 0:
            key_claim_total = len(architect_claim_paths)
        if key_claim_total > 0:
            key_claim_coverage_ratio = round(len(architect_claim_paths) / key_claim_total, 4)
    raw_architect_fallback_claim_ratio = claim_coverage_meta.get("fallback_claim_ratio")
    if raw_architect_fallback_claim_ratio is None:
        architect_fallback_claim_ratio = (
            round(architect_claim_fallback_count / architect_claim_citation_count, 4)
            if architect_claim_citation_count
            else 0.0
        )
    else:
        architect_fallback_claim_ratio = _to_float(raw_architect_fallback_claim_ratio, default=0.0)
    return {
        "architect_rag_enabled": bool(state.get("architect_rag_enabled", True)),
        "toc_schema_valid": bool(toc_validation.get("valid")),
        "toc_schema_name": toc_validation.get("schema_name"),
        "has_toc_draft": bool(state.get("toc_draft")),
        "has_logframe_draft": bool(state.get("logframe_draft")),
        "quality_score": _to_float(state.get("quality_score"), default=0.0),
        "critic_score": _to_float(state.get("critic_score"), default=0.0),
        "needs_revision": bool(state.get("needs_revision")),
        "fatal_flaw_count": len(fatal_flaws),
        "high_severity_fatal_flaw_count": high_flaws,
        "llm_finding_label_counts": llm_finding_label_counts,
        "llm_advisory_applied_label_counts": llm_advisory_applied_label_counts,
        "llm_advisory_rejected_label_counts": llm_advisory_rejected_label_counts,
        "citations_total": len(citations),
        "architect_citation_count": _count_stage_citations(citations, "architect"),
        "architect_claim_citation_count": architect_claim_citation_count,
        "mel_citation_count": _count_stage_citations(citations, "mel"),
        "high_confidence_citation_count": high_confidence_count,
        "architect_threshold_hit_rate": (
            round(architect_threshold_hits / architect_threshold_considered, 4)
            if architect_threshold_considered
            else 0.0
        ),
        "architect_key_claim_coverage_ratio": round(key_claim_coverage_ratio, 4),
        "architect_fallback_claim_ratio": round(architect_fallback_claim_ratio, 4),
        "citation_confidence_avg": (
            round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0
        ),
        "low_confidence_citation_count": low_confidence_count,
        "rag_low_confidence_citation_count": rag_low_confidence_count,
        "fallback_namespace_citation_count": fallback_namespace_count,
        "strategy_reference_citation_count": strategy_reference_count,
        "retrieval_grounded_citation_count": retrieval_grounded_count,
        "non_retrieval_citation_count": non_retrieval_count,
        "non_retrieval_citation_rate": (round(non_retrieval_count / len(citations), 4) if citations else 0.0),
        "retrieval_grounded_citation_rate": (round(retrieval_grounded_count / len(citations), 4) if citations else 0.0),
        "doc_id_present_citation_count": doc_id_present_count,
        "doc_id_present_citation_rate": (round(doc_id_present_count / len(citations), 4) if citations else 0.0),
        "retrieval_rank_present_citation_count": retrieval_rank_present_count,
        "retrieval_rank_present_citation_rate": (
            round(retrieval_rank_present_count / len(citations), 4) if citations else 0.0
        ),
        "retrieval_confidence_present_citation_count": retrieval_confidence_present_count,
        "retrieval_confidence_present_citation_rate": (
            round(retrieval_confidence_present_count / len(citations), 4) if citations else 0.0
        ),
        "retrieval_metadata_complete_citation_count": retrieval_metadata_complete_count,
        "retrieval_metadata_complete_citation_rate": (
            round(retrieval_metadata_complete_count / len(citations), 4) if citations else 0.0
        ),
        "traceability_complete_citation_count": traceability_complete_count,
        "traceability_partial_citation_count": traceability_partial_count,
        "traceability_missing_citation_count": traceability_missing_count,
        "traceability_gap_citation_count": traceability_partial_count + traceability_missing_count,
        "traceability_gap_citation_rate": (
            round((traceability_partial_count + traceability_missing_count) / len(citations), 4) if citations else 0.0
        ),
        "draft_version_count": len(draft_versions),
        "error_count": len(errors),
    }


def evaluate_expectations(metrics: dict[str, Any], expectations: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def _add_check(name: str, passed: bool, *, expected: Any, actual: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "expected": expected, "actual": actual})

    if "toc_schema_valid" in expectations:
        expected = bool(expectations["toc_schema_valid"])
        actual = bool(metrics.get("toc_schema_valid"))
        _add_check("toc_schema_valid", actual is expected, expected=expected, actual=actual)

    if "expect_needs_revision" in expectations:
        expected = bool(expectations["expect_needs_revision"])
        actual = bool(metrics.get("needs_revision"))
        _add_check("needs_revision", actual is expected, expected=expected, actual=actual)

    for key, metric_key in (
        ("min_fatal_flaws", "fatal_flaw_count"),
        ("min_high_severity_fatal_flaws", "high_severity_fatal_flaw_count"),
        ("min_quality_score", "quality_score"),
        ("min_critic_score", "critic_score"),
        ("min_retrieval_grounded_citation_rate", "retrieval_grounded_citation_rate"),
        ("min_citations_total", "citations_total"),
        ("min_architect_citations", "architect_citation_count"),
        ("min_architect_claim_citations", "architect_claim_citation_count"),
        ("min_mel_citations", "mel_citation_count"),
        ("min_high_confidence_citations", "high_confidence_citation_count"),
        ("min_architect_threshold_hit_rate", "architect_threshold_hit_rate"),
        ("min_architect_key_claim_coverage_ratio", "architect_key_claim_coverage_ratio"),
        ("min_citation_confidence_avg", "citation_confidence_avg"),
        ("min_doc_id_present_citation_rate", "doc_id_present_citation_rate"),
        ("min_retrieval_rank_present_citation_rate", "retrieval_rank_present_citation_rate"),
        ("min_retrieval_confidence_present_citation_rate", "retrieval_confidence_present_citation_rate"),
        ("min_retrieval_metadata_complete_citation_rate", "retrieval_metadata_complete_citation_rate"),
        ("min_draft_versions", "draft_version_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) >= float(expected), expected=expected, actual=actual)

    for key, metric_key in (
        ("max_quality_score", "quality_score"),
        ("max_critic_score", "critic_score"),
        ("max_fatal_flaws", "fatal_flaw_count"),
        ("max_high_severity_fatal_flaws", "high_severity_fatal_flaw_count"),
        ("max_low_confidence_citations", "low_confidence_citation_count"),
        ("max_rag_low_confidence_citations", "rag_low_confidence_citation_count"),
        ("max_fallback_namespace_citations", "fallback_namespace_citation_count"),
        ("max_non_retrieval_citation_rate", "non_retrieval_citation_rate"),
        ("max_traceability_gap_citation_rate", "traceability_gap_citation_rate"),
        ("max_architect_fallback_claim_ratio", "architect_fallback_claim_ratio"),
        ("max_errors", "error_count"),
    ):
        if key in expectations:
            expected = expectations[key]
            actual = metrics.get(metric_key, 0)
            _add_check(key, float(actual) <= float(expected), expected=expected, actual=actual)

    if expectations.get("require_toc_draft"):
        _add_check(
            "require_toc_draft", bool(metrics.get("has_toc_draft")), expected=True, actual=metrics.get("has_toc_draft")
        )
    if expectations.get("require_logframe_draft"):
        _add_check(
            "require_logframe_draft",
            bool(metrics.get("has_logframe_draft")),
            expected=True,
            actual=metrics.get("has_logframe_draft"),
        )

    passed = all(bool(c.get("passed")) for c in checks) if checks else True
    return passed, checks


def run_eval_case(case: dict[str, Any], *, skip_expectations: bool = False) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "unnamed_case")
    donor_id = str(case.get("donor_id") or "")
    final_state = grantflow_graph.invoke(build_initial_state(case))
    metrics = compute_state_metrics(final_state)
    expectations: dict[str, Any] = _dict_from(case.get("expectations"))
    if skip_expectations:
        passed = True
        checks: list[dict[str, Any]] = []
    else:
        passed, checks = evaluate_expectations(metrics, expectations)
    failed_checks = [c for c in checks if not c.get("passed")]

    return {
        "case_id": case_id,
        "donor_id": donor_id,
        "fixture_file": case.get("_fixture_file"),
        "passed": passed,
        "metrics": metrics,
        "expectations_skipped": bool(skip_expectations),
        "checks": checks,
        "failed_checks": failed_checks,
    }


def run_eval_suite(
    cases: list[dict[str, Any]],
    *,
    suite_label: str | None = None,
    skip_expectations: bool = False,
) -> dict[str, Any]:
    results = [run_eval_case(case, skip_expectations=skip_expectations) for case in cases]
    passed_count = sum(1 for r in results if r.get("passed"))
    return {
        "suite_label": str(suite_label or "baseline"),
        "expectations_skipped": bool(skip_expectations),
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "cases": results,
    }


def format_eval_suite_report(suite: dict[str, Any]) -> str:
    suite_label = str(suite.get("suite_label") or "baseline")
    lines = [
        "GrantFlow evaluation suite",
        f"Suite: {suite_label}",
        f"Cases: {suite.get('case_count', 0)} | Passed: {suite.get('passed_count', 0)} | Failed: {suite.get('failed_count', 0)}",
    ]
    if bool(suite.get("expectations_skipped")):
        lines.append("Expectations: skipped (exploratory metrics-only mode)")
    for case_raw in suite.get("cases") or []:
        if not isinstance(case_raw, dict):
            continue
        case = case_raw
        prefix = "PASS" if case.get("passed") else "FAIL"
        metrics = _dict_from(case.get("metrics"))
        architect_rag_enabled = bool(metrics.get("architect_rag_enabled", True))
        citation_count = int(metrics.get("citations_total") or 0)
        fallback_count = int(metrics.get("fallback_namespace_citation_count") or 0)
        raw_non_retrieval_count = metrics.get("non_retrieval_citation_count")
        if raw_non_retrieval_count is None:
            non_retrieval_count = fallback_count + int(metrics.get("strategy_reference_citation_count") or 0)
        else:
            non_retrieval_count = _to_int(raw_non_retrieval_count, default=0)
        grounding_risk_label: str | None = None
        fallback_ratio: float | None = None
        non_retrieval_risk_label: str | None = None
        non_retrieval_ratio: float | None = None
        traceability_gap_count = int(metrics.get("traceability_gap_citation_count") or 0)
        traceability_risk_label: str | None = None
        traceability_ratio: float | None = None
        if architect_rag_enabled:
            grounding_risk_label, fallback_ratio = _fallback_dominance_label(
                fallback_count=fallback_count,
                citation_count=citation_count,
            )
            non_retrieval_risk_label, non_retrieval_ratio = _non_retrieval_dominance_label(
                non_retrieval_count=non_retrieval_count,
                citation_count=citation_count,
            )
            traceability_risk_label, traceability_ratio = _traceability_gap_label(
                gap_count=traceability_gap_count,
                citation_count=citation_count,
            )
        grounding_suffix = ""
        if grounding_risk_label and fallback_ratio is not None:
            grounding_suffix = f" grounding_risk=fallback_dominant:{grounding_risk_label}({fallback_ratio:.0%})"
        non_retrieval_suffix = ""
        if non_retrieval_risk_label and non_retrieval_ratio is not None:
            non_retrieval_suffix = (
                f" grounding_risk=non_retrieval_dominant:{non_retrieval_risk_label}({non_retrieval_ratio:.0%})"
            )
        traceability_suffix = ""
        if traceability_risk_label and traceability_ratio is not None:
            traceability_suffix = (
                f" traceability_risk=traceability_gap:{traceability_risk_label}({traceability_ratio:.0%})"
            )
        claim_cov_suffix = ""
        try:
            key_claim_cov = float(metrics.get("architect_key_claim_coverage_ratio") or 0.0)
        except (TypeError, ValueError):
            key_claim_cov = 0.0
        if key_claim_cov > 0.0:
            claim_cov_suffix = f" key_claim_cov={key_claim_cov:.0%}"
        lines.append(
            (
                f"- {prefix} {case.get('case_id')} ({case.get('donor_id')}): "
                f"q={metrics.get('quality_score')} critic={metrics.get('critic_score')} "
                f"toc_valid={metrics.get('toc_schema_valid')} flaws={metrics.get('fatal_flaw_count')} "
                f"citations={metrics.get('citations_total')}{claim_cov_suffix}{grounding_suffix}"
                f"{non_retrieval_suffix}{traceability_suffix}"
            )
        )
        for check in _list_from(case.get("failed_checks")):
            if not isinstance(check, dict):
                continue
            lines.append(f"    * {check.get('name')}: expected {check.get('expected')} got {check.get('actual')}")

    donor_rows: dict[str, dict[str, Any]] = {}
    llm_finding_label_counts_total: dict[str, int] = {}
    llm_advisory_applied_label_counts_total: dict[str, int] = {}
    llm_advisory_rejected_label_counts_total: dict[str, int] = {}
    for case in suite.get("cases") or []:
        if not isinstance(case, dict):
            continue
        donor_id = str(case.get("donor_id") or "unknown")
        metrics = _dict_from(case.get("metrics"))
        row = donor_rows.setdefault(
            donor_id,
            {
                "case_count": 0,
                "pass_count": 0,
                "quality_scores": [],
                "needs_revision_count": 0,
                "high_flaw_total": 0,
                "low_conf_total": 0,
                "fallback_ns_total": 0,
                "strategy_reference_total": 0,
                "non_retrieval_total": 0,
                "traceability_gap_total": 0,
                "traceability_partial_total": 0,
                "traceability_missing_total": 0,
                "traceability_complete_total": 0,
                "citation_total": 0,
                "rag_expected_case_count": 0,
                "rag_expected_citation_total": 0,
                "rag_expected_fallback_ns_total": 0,
                "rag_expected_non_retrieval_total": 0,
                "rag_expected_traceability_gap_total": 0,
            },
        )
        row["case_count"] = int(row["case_count"]) + 1
        if bool(case.get("passed")):
            row["pass_count"] = int(row["pass_count"]) + 1
        if isinstance(metrics.get("quality_score"), (int, float)):
            cast_scores = row.get("quality_scores")
            if isinstance(cast_scores, list):
                cast_scores.append(float(metrics.get("quality_score") or 0.0))
        if bool(metrics.get("needs_revision")):
            row["needs_revision_count"] = int(row["needs_revision_count"]) + 1
        row["high_flaw_total"] = int(row["high_flaw_total"]) + int(metrics.get("high_severity_fatal_flaw_count") or 0)
        row["low_conf_total"] = int(row["low_conf_total"]) + int(metrics.get("low_confidence_citation_count") or 0)
        row["citation_total"] = int(row["citation_total"]) + int(metrics.get("citations_total") or 0)
        row["fallback_ns_total"] = int(row["fallback_ns_total"]) + int(
            metrics.get("fallback_namespace_citation_count") or 0
        )
        strategy_reference_total = int(metrics.get("strategy_reference_citation_count") or 0)
        row["strategy_reference_total"] = int(row["strategy_reference_total"]) + strategy_reference_total
        raw_non_retrieval_total = metrics.get("non_retrieval_citation_count")
        if raw_non_retrieval_total is None:
            non_retrieval_total = int(metrics.get("fallback_namespace_citation_count") or 0) + strategy_reference_total
        else:
            non_retrieval_total = _to_int(raw_non_retrieval_total, default=0)
        row["non_retrieval_total"] = int(row["non_retrieval_total"]) + non_retrieval_total
        row["traceability_gap_total"] = int(row["traceability_gap_total"]) + int(
            metrics.get("traceability_gap_citation_count") or 0
        )
        row["traceability_partial_total"] = int(row["traceability_partial_total"]) + int(
            metrics.get("traceability_partial_citation_count") or 0
        )
        row["traceability_missing_total"] = int(row["traceability_missing_total"]) + int(
            metrics.get("traceability_missing_citation_count") or 0
        )
        row["traceability_complete_total"] = int(row["traceability_complete_total"]) + int(
            metrics.get("traceability_complete_citation_count") or 0
        )
        architect_rag_enabled = bool(metrics.get("architect_rag_enabled", True))
        if architect_rag_enabled:
            row["rag_expected_case_count"] = int(row["rag_expected_case_count"]) + 1
            row["rag_expected_citation_total"] = int(row["rag_expected_citation_total"]) + int(
                metrics.get("citations_total") or 0
            )
            row["rag_expected_fallback_ns_total"] = int(row["rag_expected_fallback_ns_total"]) + int(
                metrics.get("fallback_namespace_citation_count") or 0
            )
            row["rag_expected_non_retrieval_total"] = int(row["rag_expected_non_retrieval_total"]) + non_retrieval_total
            row["rag_expected_traceability_gap_total"] = int(row["rag_expected_traceability_gap_total"]) + int(
                metrics.get("traceability_gap_citation_count") or 0
            )
        row_label_counts = row.setdefault("llm_finding_label_counts", {})
        if not isinstance(row_label_counts, dict):
            row_label_counts = {}
            row["llm_finding_label_counts"] = row_label_counts
        case_label_counts = metrics.get("llm_finding_label_counts") if isinstance(metrics, dict) else {}
        if isinstance(case_label_counts, dict):
            for label, count in case_label_counts.items():
                label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
                row_label_counts[label_key] = int(row_label_counts.get(label_key, 0)) + int(count or 0)
                llm_finding_label_counts_total[label_key] = int(llm_finding_label_counts_total.get(label_key, 0)) + int(
                    count or 0
                )
        for metric_key, row_key, total_key in (
            (
                "llm_advisory_applied_label_counts",
                "llm_advisory_applied_label_counts",
                llm_advisory_applied_label_counts_total,
            ),
            (
                "llm_advisory_rejected_label_counts",
                "llm_advisory_rejected_label_counts",
                llm_advisory_rejected_label_counts_total,
            ),
        ):
            row_mix = row.setdefault(row_key, {})
            if not isinstance(row_mix, dict):
                row_mix = {}
                row[row_key] = row_mix
            case_mix = metrics.get(metric_key) if isinstance(metrics, dict) else {}
            if not isinstance(case_mix, dict):
                continue
            for label, count in case_mix.items():
                label_key = str(label).strip() or "GENERIC_LLM_REVIEW_FLAG"
                row_mix[label_key] = int(row_mix.get(label_key, 0)) + int(count or 0)
                total_key[label_key] = int(total_key.get(label_key, 0)) + int(count or 0)

    if donor_rows:
        lines.append("")
        lines.append("Donor quality breakdown (suite-level)")
        ordered_donors = sorted(
            donor_rows.items(),
            key=lambda item: (
                -(int(item[1].get("needs_revision_count") or 0)),
                -(int(item[1].get("high_flaw_total") or 0)),
                str(item[0]),
            ),
        )
        for donor_id, row in ordered_donors:
            quality_scores = row.get("quality_scores") if isinstance(row.get("quality_scores"), list) else []
            avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else None
            case_count = int(row.get("case_count") or 0)
            needs_revision_count = int(row.get("needs_revision_count") or 0)
            needs_revision_rate = (needs_revision_count / case_count) if case_count else 0.0
            lines.append(
                (
                    f"- {donor_id}: cases={case_count} pass={int(row.get('pass_count') or 0)}/{case_count} "
                    f"avg_q={avg_quality if avg_quality is not None else '-'} "
                    f"needs_revision={needs_revision_count} ({needs_revision_rate:.0%}) "
                    f"high_flaws={int(row.get('high_flaw_total') or 0)} "
                    f"low_conf_citations={int(row.get('low_conf_total') or 0)} "
                    f"fallback_ns_citations={int(row.get('fallback_ns_total') or 0)} "
                    f"strategy_ref_citations={int(row.get('strategy_reference_total') or 0)} "
                    f"non_retrieval_citations={int(row.get('non_retrieval_total') or 0)} "
                    f"traceability_gap_citations={int(row.get('traceability_gap_total') or 0)} "
                    f"rag_expected_cases={int(row.get('rag_expected_case_count') or 0)}"
                )
            )
        risky_donors: list[tuple[str, dict[str, Any], float, str]] = []
        for donor_id, row in donor_rows.items():
            citation_total = int(row.get("rag_expected_citation_total") or 0)
            fallback_total = int(row.get("rag_expected_fallback_ns_total") or 0)
            label, ratio = _fallback_dominance_label(fallback_count=fallback_total, citation_count=citation_total)
            if label and ratio is not None:
                risky_donors.append((donor_id, row, ratio, label))
        if risky_donors:
            lines.append("")
            lines.append("Grounding risk summary (fallback dominance)")
            risky_donors.sort(key=lambda item: (-item[2], -int(item[1].get("rag_expected_citation_total") or 0), item[0]))
            for donor_id, row, ratio, label in risky_donors:
                lines.append(
                    (
                        f"- {donor_id}: fallback_dominance={label} ({ratio:.0%}) "
                        f"fallback_ns_citations={int(row.get('rag_expected_fallback_ns_total') or 0)}/"
                        f"{int(row.get('rag_expected_citation_total') or 0)}"
                    )
                )
        non_retrieval_risky_donors: list[tuple[str, dict[str, Any], float, str]] = []
        for donor_id, row in donor_rows.items():
            citation_total = int(row.get("rag_expected_citation_total") or 0)
            non_retrieval_total = int(row.get("rag_expected_non_retrieval_total") or 0)
            label, ratio = _non_retrieval_dominance_label(
                non_retrieval_count=non_retrieval_total,
                citation_count=citation_total,
            )
            if label and ratio is not None:
                non_retrieval_risky_donors.append((donor_id, row, ratio, label))
        if non_retrieval_risky_donors:
            lines.append("")
            lines.append("Grounding risk summary (non-retrieval dominance)")
            non_retrieval_risky_donors.sort(
                key=lambda item: (-item[2], -int(item[1].get("rag_expected_citation_total") or 0), item[0])
            )
            for donor_id, row, ratio, label in non_retrieval_risky_donors:
                lines.append(
                    (
                        f"- {donor_id}: non_retrieval_dominance={label} ({ratio:.0%}) "
                        f"non_retrieval_citations={int(row.get('rag_expected_non_retrieval_total') or 0)}/"
                        f"{int(row.get('rag_expected_citation_total') or 0)} "
                        f"(fallback={int(row.get('rag_expected_fallback_ns_total') or 0)}, "
                        f"strategy_ref={max(0, int(row.get('rag_expected_non_retrieval_total') or 0) - int(row.get('rag_expected_fallback_ns_total') or 0))})"
                    )
                )
    if llm_finding_label_counts_total:
        lines.append("")
        lines.append("LLM finding label mix (suite-level)")
        for label, count in sorted(
            llm_finding_label_counts_total.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            lines.append(f"- {label}: {int(count)}")

        donor_label_mix_rows: list[tuple[str, dict[str, int]]] = []
        for donor_id, row in donor_rows.items():
            donor_label_counts = row.get("llm_finding_label_counts")
            if isinstance(donor_label_counts, dict) and donor_label_counts:
                donor_label_mix_rows.append((donor_id, donor_label_counts))
        if donor_label_mix_rows:
            lines.append("")
            lines.append("LLM finding label mix by donor")
            for donor_id, donor_label_counts in sorted(donor_label_mix_rows, key=lambda item: str(item[0])):
                top_entries = sorted(
                    donor_label_counts.items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )[:5]
                top_str = ", ".join(f"{label}={int(count)}" for label, count in top_entries)
                lines.append(f"- {donor_id}: {top_str}")
    for title, total_mix, donor_key in (
        (
            "LLM advisory label mix (applied)",
            llm_advisory_applied_label_counts_total,
            "llm_advisory_applied_label_counts",
        ),
        (
            "LLM advisory label mix (rejected)",
            llm_advisory_rejected_label_counts_total,
            "llm_advisory_rejected_label_counts",
        ),
    ):
        if not total_mix:
            continue
        lines.append("")
        lines.append(title)
        for label, count in sorted(total_mix.items(), key=lambda item: (-int(item[1]), str(item[0]))):
            lines.append(f"- {label}: {int(count)}")
        donor_mix_rows: list[tuple[str, dict[str, int]]] = []
        for donor_id, row in donor_rows.items():
            donor_mix = row.get(donor_key)
            if isinstance(donor_mix, dict) and donor_mix:
                donor_mix_rows.append((donor_id, donor_mix))
        if donor_mix_rows:
            lines.append("")
            lines.append(f"{title} by donor")
            for donor_id, donor_mix in sorted(donor_mix_rows, key=lambda item: str(item[0])):
                top_entries = sorted(donor_mix.items(), key=lambda item: (-int(item[1]), str(item[0])))[:5]
                top_str = ", ".join(f"{label}={int(count)}" for label, count in top_entries)
                lines.append(f"- {donor_id}: {top_str}")
    return "\n".join(lines)


def build_regression_baseline_snapshot(suite: dict[str, Any]) -> dict[str, Any]:
    case_map: dict[str, Any] = {}
    for case in suite.get("cases") or []:
        case_id = str(case.get("case_id") or "")
        if not case_id:
            continue
        metrics = case.get("metrics") if isinstance(case.get("metrics"), dict) else {}
        case_map[case_id] = {
            "donor_id": case.get("donor_id"),
            "metrics": {
                key: metrics.get(key)
                for key in (
                    *HIGHER_IS_BETTER_METRICS,
                    *LOWER_IS_BETTER_METRICS,
                    *BOOLEAN_GUARDRAIL_METRICS,
                    "needs_revision",
                )
            },
        }
    return {
        "schema_version": 1,
        "tracked_metrics": {
            "higher_is_better": list(HIGHER_IS_BETTER_METRICS),
            "lower_is_better": list(LOWER_IS_BETTER_METRICS),
            "boolean_guardrails": list(BOOLEAN_GUARDRAIL_METRICS) + ["needs_revision"],
        },
        "cases": case_map,
    }


def compare_suite_to_baseline(
    suite: dict[str, Any], baseline: dict[str, Any], *, tolerance: float = REGRESSION_TOLERANCE
) -> dict[str, Any]:
    baseline_cases = _dict_from(baseline.get("cases")) if isinstance(baseline, dict) else {}
    current_cases = {
        str(case.get("case_id") or ""): case
        for case in (suite.get("cases") or [])
        if isinstance(case, dict) and str(case.get("case_id") or "")
    }

    regressions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def _case_donor_id(case_payload: Any, fallback: str = "unknown") -> str:
        if isinstance(case_payload, dict):
            donor = case_payload.get("donor_id")
            if donor:
                return str(donor)
        return fallback

    for case_id, current_case in current_cases.items():
        current_donor_id = _case_donor_id(current_case)
        current_metrics = _dict_from(current_case.get("metrics"))
        baseline_case = baseline_cases.get(case_id)
        if not isinstance(baseline_case, dict):
            warnings.append(
                {
                    "type": "new_case_not_in_baseline",
                    "case_id": case_id,
                    "donor_id": current_donor_id,
                    "message": "Current eval case is not present in baseline snapshot.",
                }
            )
            continue

        baseline_metrics = _dict_from(baseline_case.get("metrics"))

        for metric in HIGHER_IS_BETTER_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = float(baseline_metrics[metric] or 0.0)
            current_value = float(current_metrics[metric] or 0.0)
            if current_value + tolerance < baseline_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "donor_id": current_donor_id,
                        "metric": metric,
                        "direction": "higher_is_better",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} decreased below baseline",
                    }
                )

        for metric in LOWER_IS_BETTER_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = float(baseline_metrics[metric] or 0.0)
            current_value = float(current_metrics[metric] or 0.0)
            if current_value > baseline_value + tolerance:
                regressions.append(
                    {
                        "case_id": case_id,
                        "donor_id": current_donor_id,
                        "metric": metric,
                        "direction": "lower_is_better",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} increased above baseline",
                    }
                )

        for metric in BOOLEAN_GUARDRAIL_METRICS:
            if metric not in baseline_metrics or metric not in current_metrics:
                continue
            baseline_value = bool(baseline_metrics[metric])
            current_value = bool(current_metrics[metric])
            if baseline_value and not current_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "donor_id": current_donor_id,
                        "metric": metric,
                        "direction": "boolean_guardrail",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": f"{metric} regressed from true to false",
                    }
                )

        if "needs_revision" in baseline_metrics and "needs_revision" in current_metrics:
            baseline_value = bool(baseline_metrics["needs_revision"])
            current_value = bool(current_metrics["needs_revision"])
            if not baseline_value and current_value:
                regressions.append(
                    {
                        "case_id": case_id,
                        "donor_id": current_donor_id,
                        "metric": "needs_revision",
                        "direction": "boolean_guardrail",
                        "baseline": baseline_value,
                        "current": current_value,
                        "message": "needs_revision changed from false to true",
                    }
                )

    for case_id in baseline_cases:
        if case_id not in current_cases:
            warnings.append(
                {
                    "type": "baseline_case_missing_in_current_suite",
                    "case_id": case_id,
                    "donor_id": _case_donor_id(baseline_cases.get(case_id)),
                    "message": "Baseline snapshot contains a case not present in current suite.",
                }
            )

    donor_breakdown: dict[str, dict[str, Any]] = {}
    for item in regressions:
        donor_id = str(item.get("donor_id") or "unknown")
        row = donor_breakdown.setdefault(
            donor_id,
            {
                "regression_count": 0,
                "warning_count": 0,
                "metrics": {},
            },
        )
        row["regression_count"] = int(row.get("regression_count") or 0) + 1
        metrics_map = row.get("metrics")
        if isinstance(metrics_map, dict):
            metric_name = str(item.get("metric") or "unknown")
            metrics_map[metric_name] = int(metrics_map.get(metric_name) or 0) + 1
    for item in warnings:
        donor_id = str(item.get("donor_id") or "unknown")
        row = donor_breakdown.setdefault(
            donor_id,
            {
                "regression_count": 0,
                "warning_count": 0,
                "metrics": {},
            },
        )
        row["warning_count"] = int(row.get("warning_count") or 0) + 1

    priority_metric_breakdown: dict[str, dict[str, Any]] = {}
    donor_priority_breakdown: dict[str, dict[str, Any]] = {}
    severity_weighted_regression_score = 0
    high_priority_regression_count = 0
    for item in regressions:
        metric = str(item.get("metric") or "unknown")
        donor_id = str(item.get("donor_id") or "unknown")
        weight = int(REGRESSION_PRIORITY_WEIGHTS.get(metric, 1))
        weighted_score = weight
        severity_weighted_regression_score += weighted_score
        if weight >= 4:
            high_priority_regression_count += 1

        metric_row = priority_metric_breakdown.setdefault(
            metric,
            {"count": 0, "weight": weight, "weighted_score": 0},
        )
        metric_row["count"] = int(metric_row.get("count") or 0) + 1
        metric_row["weighted_score"] = int(metric_row.get("weighted_score") or 0) + weighted_score

        donor_row = donor_priority_breakdown.setdefault(
            donor_id,
            {"regression_count": 0, "weighted_score": 0, "high_priority_regression_count": 0},
        )
        donor_row["regression_count"] = int(donor_row.get("regression_count") or 0) + 1
        donor_row["weighted_score"] = int(donor_row.get("weighted_score") or 0) + weighted_score
        if weight >= 4:
            donor_row["high_priority_regression_count"] = int(donor_row.get("high_priority_regression_count") or 0) + 1

    return {
        "baseline_path": None,
        "case_count": len(current_cases),
        "baseline_case_count": len(baseline_cases),
        "regression_count": len(regressions),
        "warning_count": len(warnings),
        "has_regressions": bool(regressions),
        "regressions": regressions,
        "warnings": warnings,
        "donor_breakdown": donor_breakdown,
        "severity_weighted_regression_score": severity_weighted_regression_score,
        "high_priority_regression_count": high_priority_regression_count,
        "priority_metric_breakdown": priority_metric_breakdown,
        "donor_priority_breakdown": donor_priority_breakdown,
    }


def format_eval_comparison_report(comparison: dict[str, Any]) -> str:
    lines = [
        "GrantFlow evaluation baseline comparison",
        (
            f"Current cases: {comparison.get('case_count', 0)} | "
            f"Baseline cases: {comparison.get('baseline_case_count', 0)} | "
            f"Regressions: {comparison.get('regression_count', 0)} | "
            f"Warnings: {comparison.get('warning_count', 0)}"
        ),
    ]
    for item in comparison.get("regressions") or []:
        lines.append(
            (
                f"- REGRESSION {item.get('case_id')} ({item.get('donor_id') or 'unknown'}) {item.get('metric')}: "
                f"baseline={item.get('baseline')} current={item.get('current')} "
                f"({item.get('message')})"
            )
        )
    for item in comparison.get("warnings") or []:
        lines.append(f"- WARNING {item.get('case_id')} ({item.get('donor_id') or 'unknown'}): {item.get('message')}")

    donor_breakdown = comparison.get("donor_breakdown")
    if isinstance(donor_breakdown, dict) and donor_breakdown:
        lines.append("")
        lines.append("Donor regression breakdown")
        ordered = sorted(
            donor_breakdown.items(),
            key=lambda item: (
                -(int((item[1] or {}).get("regression_count") or 0)),
                -(int((item[1] or {}).get("warning_count") or 0)),
                str(item[0]),
            ),
        )
        for donor_id, row in ordered:
            row_dict = row if isinstance(row, dict) else {}
            metrics_map = _dict_from(row_dict.get("metrics"))
            top_metrics = sorted(
                ((str(k), int(v or 0)) for k, v in metrics_map.items()),
                key=lambda kv: (-kv[1], kv[0]),
            )[:3]
            metric_text = ", ".join(f"{name}x{count}" for name, count in top_metrics) if top_metrics else "-"
            lines.append(
                (
                    f"- {donor_id}: regressions={int(row_dict.get('regression_count') or 0)} "
                    f"warnings={int(row_dict.get('warning_count') or 0)} top_metrics={metric_text}"
                )
            )

    priority_metric_breakdown = comparison.get("priority_metric_breakdown")
    donor_priority_breakdown = comparison.get("donor_priority_breakdown")
    if isinstance(priority_metric_breakdown, dict) and priority_metric_breakdown:
        lines.append("")
        lines.append(
            "Severity-weighted regression summary "
            f"(weighted_score={int(comparison.get('severity_weighted_regression_score') or 0)}, "
            f"high_priority={int(comparison.get('high_priority_regression_count') or 0)})"
        )
        ordered_metrics = sorted(
            priority_metric_breakdown.items(),
            key=lambda item: (
                -(int((item[1] or {}).get("weighted_score") or 0)),
                -(int((item[1] or {}).get("count") or 0)),
                str(item[0]),
            ),
        )
        for metric, row in ordered_metrics[:8]:
            row_dict = row if isinstance(row, dict) else {}
            lines.append(
                (
                    f"- metric {metric}: count={int(row_dict.get('count') or 0)} "
                    f"weight={int(row_dict.get('weight') or 1)} "
                    f"weighted_score={int(row_dict.get('weighted_score') or 0)}"
                )
            )
        if isinstance(donor_priority_breakdown, dict) and donor_priority_breakdown:
            lines.append("Top donor weighted risk")
            ordered_donors = sorted(
                donor_priority_breakdown.items(),
                key=lambda item: (
                    -(int((item[1] or {}).get("weighted_score") or 0)),
                    -(int((item[1] or {}).get("high_priority_regression_count") or 0)),
                    str(item[0]),
                ),
            )
            for donor_id, row in ordered_donors[:8]:
                row_dict = row if isinstance(row, dict) else {}
                lines.append(
                    (
                        f"- {donor_id}: weighted_score={int(row_dict.get('weighted_score') or 0)} "
                        f"regressions={int(row_dict.get('regression_count') or 0)} "
                        f"high_priority={int(row_dict.get('high_priority_regression_count') or 0)}"
                    )
                )
    if not (comparison.get("regressions") or comparison.get("warnings")):
        lines.append("- No regressions detected against baseline.")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GrantFlow baseline evaluation fixtures.")
    sample_ids_help = ", ".join(available_sample_ids())
    parser.add_argument(
        "--suite-label",
        type=str,
        default="baseline",
        help="Label to include in reports/artifacts (for example: baseline, llm-eval).",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Override fixture settings and run all cases with llm_mode=true.",
    )
    architect_rag_group = parser.add_mutually_exclusive_group()
    architect_rag_group.add_argument(
        "--force-architect-rag",
        action="store_true",
        help="Override fixture settings and run all cases with architect_rag_enabled=true.",
    )
    architect_rag_group.add_argument(
        "--force-no-architect-rag",
        action="store_true",
        help="Override fixture settings and run all cases with architect_rag_enabled=false.",
    )
    parser.add_argument(
        "--skip-expectations",
        action="store_true",
        help="Skip fixture expectation assertions and collect metrics only (exploratory mode).",
    )
    parser.add_argument(
        "--donor-id",
        action="append",
        default=[],
        help="Filter suite to one or more donor_ids (repeat flag or use comma-separated values).",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Filter suite to one or more case_ids (repeat flag or use comma-separated values).",
    )
    parser.add_argument(
        "--cases-file",
        action="append",
        default=[],
        help="Explicit JSON file(s) with eval cases (repeat flag or use comma-separated values).",
    )
    parser.add_argument(
        "--sample-id",
        action="append",
        default=[],
        help=(
            "Use built-in sample preset case(s) from docs/samples JSON payloads "
            f"(repeat flag or use comma-separated values). Available: {sample_ids_help}. "
            "Use 'all' to include all sample presets."
        ),
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Limit number of selected cases after donor/case filters (0 = no limit).",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=None,
        help="Deterministic random seed for case subsampling when --max-cases is set.",
    )
    parser.add_argument(
        "--seed-rag-manifest",
        type=Path,
        default=None,
        help="Optional JSONL manifest to seed donor namespaces before running eval cases.",
    )
    parser.add_argument(
        "--seed-rag-best-effort",
        action="store_true",
        help="Do not fail when manifest seeding reports errors.",
    )
    parser.add_argument(
        "--require-seed-readiness",
        action="store_true",
        help=(
            "Fail before eval run when expected_doc_families (from selected cases) "
            "are not fully covered by seeded manifest uploads."
        ),
    )
    parser.add_argument(
        "--seed-readiness-min-per-family",
        type=int,
        default=1,
        help="Minimum number of seeded docs required per expected doc_family when --require-seed-readiness is set.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write raw suite results as JSON to this path.",
    )
    parser.add_argument(
        "--text-out",
        type=Path,
        default=None,
        help="Write formatted text summary to this path.",
    )
    parser.add_argument(
        "--baseline-snapshot-out",
        type=Path,
        default=None,
        help="Write a baseline snapshot JSON (used for future regression comparisons).",
    )
    parser.add_argument(
        "--compare-to-baseline",
        type=Path,
        default=None,
        help="Compare current suite metrics to a baseline snapshot JSON and fail only on regressions.",
    )
    parser.add_argument(
        "--comparison-json-out",
        type=Path,
        default=None,
        help="Write baseline comparison result JSON to this path.",
    )
    parser.add_argument(
        "--comparison-text-out",
        type=Path,
        default=None,
        help="Write formatted baseline comparison summary to this path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    case_file_tokens = _split_csv_args(args.cases_file)
    sample_id_tokens = _split_csv_args(args.sample_id)
    case_files = [Path(token) for token in case_file_tokens]
    if case_files:
        cases = load_eval_cases(case_files=case_files)
    elif sample_id_tokens:
        cases = []
    else:
        cases = load_eval_cases()
    if sample_id_tokens:
        try:
            sample_cases = load_sample_eval_cases(sample_id_tokens)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if case_files:
            cases.extend(sample_cases)
        else:
            cases = sample_cases
    donor_filters = _split_csv_args(args.donor_id)
    case_filters = _split_csv_args(args.case_id)
    cases = filter_eval_cases(cases, donor_ids=donor_filters, case_ids=case_filters)
    max_cases = int(args.max_cases or 0)
    cases = limit_eval_cases(
        cases,
        max_cases=max_cases if max_cases > 0 else None,
        sample_seed=(int(args.sample_seed) if args.sample_seed is not None else None),
    )
    if not cases:
        print("No eval cases matched the provided filters.", file=sys.stderr)
        return 2
    cases = apply_runtime_overrides_to_cases(
        cases,
        force_llm=bool(args.force_llm),
        force_architect_rag=bool(args.force_architect_rag),
        force_no_architect_rag=bool(args.force_no_architect_rag),
    )
    seeded_corpus_summary: dict[str, Any] | None = None
    if args.seed_rag_manifest is not None:
        donor_ids_for_seed = sorted(
            {str(case.get("donor_id") or "").strip().lower() for case in cases if case.get("donor_id")}
        )
        seeded_corpus_summary = seed_rag_corpus_from_manifest(
            args.seed_rag_manifest,
            allowed_donor_ids=donor_ids_for_seed,
        )
        seed_errors = list(seeded_corpus_summary.get("errors") or [])
        if seed_errors and not bool(args.seed_rag_best_effort):
            print("RAG corpus seeding failed:")
            for item in seed_errors:
                print(f"- {item}")
            return 1
    expected_families = expected_doc_families_by_donor(cases)
    seed_readiness: dict[str, Any] | None = None
    if seeded_corpus_summary is not None and expected_families:
        seed_readiness = evaluate_seed_readiness(
            seeded_summary=seeded_corpus_summary,
            expected_doc_families=expected_families,
            min_uploads_per_family=int(args.seed_readiness_min_per_family or 1),
        )
    if bool(args.require_seed_readiness):
        if args.seed_rag_manifest is None:
            print("Seed readiness check requires --seed-rag-manifest.", file=sys.stderr)
            return 2
        if not expected_families:
            print("Seed readiness check requires expected_doc_families in selected eval cases.", file=sys.stderr)
            return 2
        if not seed_readiness or not bool(seed_readiness.get("all_ready")):
            print("Seed readiness check failed:")
            donors = seed_readiness.get("donors") if isinstance(seed_readiness, dict) else {}
            donor_rows = donors if isinstance(donors, dict) else {}
            for donor_id in sorted(donor_rows.keys()):
                row = donor_rows[donor_id] if isinstance(donor_rows.get(donor_id), dict) else {}
                missing = row.get("missing_doc_families") if isinstance(row.get("missing_doc_families"), list) else []
                underfilled = (
                    row.get("underfilled_doc_families") if isinstance(row.get("underfilled_doc_families"), list) else []
                )
                if missing:
                    print(f"- {donor_id}: missing_doc_families={','.join(str(v) for v in missing)}")
                if underfilled:
                    print(f"- {donor_id}: underfilled_doc_families={','.join(str(v) for v in underfilled)}")
            return 1
    suite = run_eval_suite(cases, suite_label=args.suite_label, skip_expectations=bool(args.skip_expectations))
    suite["runtime_overrides"] = {
        "force_llm": bool(args.force_llm),
        "force_architect_rag": bool(args.force_architect_rag),
        "force_no_architect_rag": bool(args.force_no_architect_rag),
    }
    suite["runtime_overrides"]["skip_expectations"] = bool(args.skip_expectations)
    suite["runtime_overrides"]["donor_filters"] = donor_filters
    suite["runtime_overrides"]["case_filters"] = case_filters
    suite["runtime_overrides"]["cases_files"] = case_file_tokens
    suite["runtime_overrides"]["sample_ids"] = sample_id_tokens
    suite["runtime_overrides"]["max_cases"] = max_cases if max_cases > 0 else None
    suite["runtime_overrides"]["sample_seed"] = (
        int(args.sample_seed) if args.sample_seed is not None and max_cases > 0 else None
    )
    if args.seed_rag_manifest is not None:
        suite["runtime_overrides"]["seed_rag_manifest"] = str(args.seed_rag_manifest)
        suite["runtime_overrides"]["seed_rag_best_effort"] = bool(args.seed_rag_best_effort)
        suite["runtime_overrides"]["require_seed_readiness"] = bool(args.require_seed_readiness)
        suite["runtime_overrides"]["seed_readiness_min_per_family"] = max(1, int(args.seed_readiness_min_per_family))
    if seeded_corpus_summary is not None:
        suite["seeded_corpus"] = seeded_corpus_summary
    if seed_readiness is not None:
        suite["seeded_corpus_readiness"] = seed_readiness
    text_report = format_eval_suite_report(suite)
    print(text_report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(suite, indent=2, sort_keys=True), encoding="utf-8")
    if args.text_out is not None:
        args.text_out.parent.mkdir(parents=True, exist_ok=True)
        args.text_out.write_text(text_report + "\n", encoding="utf-8")
    if args.baseline_snapshot_out is not None:
        snapshot = build_regression_baseline_snapshot(suite)
        args.baseline_snapshot_out.parent.mkdir(parents=True, exist_ok=True)
        args.baseline_snapshot_out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    comparison: dict[str, Any] | None = None
    if args.compare_to_baseline is not None:
        baseline = json.loads(args.compare_to_baseline.read_text(encoding="utf-8"))
        comparison = compare_suite_to_baseline(suite, baseline)
        comparison["baseline_path"] = str(args.compare_to_baseline)
        comparison_text = format_eval_comparison_report(comparison)
        print()
        print(comparison_text)
        if args.comparison_json_out is not None:
            args.comparison_json_out.parent.mkdir(parents=True, exist_ok=True)
            args.comparison_json_out.write_text(json.dumps(comparison, indent=2, sort_keys=True), encoding="utf-8")
        if args.comparison_text_out is not None:
            args.comparison_text_out.parent.mkdir(parents=True, exist_ok=True)
            args.comparison_text_out.write_text(comparison_text + "\n", encoding="utf-8")

    suite_ok = True if bool(args.skip_expectations) else bool(suite.get("all_passed"))
    comparison_ok = comparison is None or not bool(comparison.get("has_regressions"))
    return 0 if (suite_ok and comparison_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
