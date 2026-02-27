from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

from grantflow.swarm.critic_donor_policy import apply_donor_specific_toc_checks
from grantflow.swarm.state_contract import state_input_context
from grantflow.swarm.versioning import filter_versions


class CriticFatalFlaw(BaseModel):
    finding_id: Optional[str] = Field(default=None, description="Stable finding identifier within a job")
    code: str = Field(description="Stable rule/check code")
    label: Optional[str] = Field(default=None, description="Normalized finding label for stable downstream handling")
    severity: str = Field(description="Severity level: low|medium|high")
    section: str = Field(description="Affected section: toc|logframe|general")
    status: Optional[str] = Field(default=None, description="open|acknowledged|resolved")
    version_id: Optional[str] = Field(default=None, description="Related draft version id, if available")
    message: str = Field(description="Human-readable issue summary")
    rationale: Optional[str] = Field(default=None, description="Why this finding matters")
    fix_suggestion: Optional[str] = Field(default=None, description="Suggested remediation")
    fix_hint: Optional[str] = Field(default=None, description="Suggested fix")
    acknowledged_at: Optional[str] = Field(default=None, description="Timestamp when acknowledged")
    resolved_at: Optional[str] = Field(default=None, description="Timestamp when resolved")
    source: str = Field(default="rules", description="rules or llm")


class RuleCheckResult(BaseModel):
    code: str
    status: str  # pass|warn|fail
    section: str
    detail: Optional[str] = None


class RuleCriticReport(BaseModel):
    score: float
    fatal_flaws: List[CriticFatalFlaw]
    checks: List[RuleCheckResult]
    revision_instructions: str


def _latest_version_id(state: Dict[str, Any], section: str) -> Optional[str]:
    raw_versions = state.get("draft_versions")
    if not isinstance(raw_versions, list):
        return None
    versions = filter_versions([v for v in raw_versions if isinstance(v, dict)], section=section)
    if not versions:
        return None
    return str(versions[-1].get("version_id") or "") or None


def _add_flaw(
    flaws: List[CriticFatalFlaw],
    *,
    code: str,
    severity: str,
    section: str,
    state: Dict[str, Any],
    message: str,
    fix_hint: Optional[str],
) -> None:
    flaws.append(
        CriticFatalFlaw(
            code=code,
            severity=severity,
            section=section,
            version_id=_latest_version_id(state, section) if section in {"toc", "logframe"} else None,
            message=message,
            rationale=message,
            fix_suggestion=fix_hint,
            fix_hint=fix_hint,
            source="rules",
        )
    )


def _iter_citations(state: Dict[str, Any], stage: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    raw = state.get("citations")
    if not isinstance(raw, list):
        return []
    rows = [c for c in raw if isinstance(c, dict)]
    if stage is not None:
        rows = [c for c in rows if str(c.get("stage") or "") == stage]
    return rows


def _check(
    checks: List[RuleCheckResult],
    *,
    code: str,
    status: str,
    section: str,
    detail: Optional[str] = None,
) -> None:
    checks.append(RuleCheckResult(code=code, status=status, section=section, detail=detail))


def evaluate_rule_based_critic(state: Dict[str, Any]) -> RuleCriticReport:
    checks: List[RuleCheckResult] = []
    flaws: List[CriticFatalFlaw] = []

    raw_input_context = state_input_context(state)
    non_empty_input_fields = 0
    for value in raw_input_context.values():
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                non_empty_input_fields += 1
            continue
        if isinstance(value, (list, dict, tuple, set)):
            if len(value) > 0:
                non_empty_input_fields += 1
            continue
        non_empty_input_fields += 1

    if non_empty_input_fields >= 2:
        checks.append(
            RuleCheckResult(
                code="INPUT_BRIEF_MINIMUM_CONTEXT",
                status="pass",
                section="general",
                detail=f"{non_empty_input_fields} non-empty input field(s)",
            )
        )
    else:
        checks.append(
            RuleCheckResult(
                code="INPUT_BRIEF_MINIMUM_CONTEXT",
                status="fail",
                section="general",
                detail=f"{non_empty_input_fields} non-empty input field(s); need at least 2",
            )
        )
        _add_flaw(
            flaws,
            code="INPUT_BRIEF_TOO_SPARSE",
            severity="high",
            section="general",
            state=state,
            message="Input brief is too sparse for reliable drafting and review.",
            fix_hint="Provide at least a project title plus one additional field (for example country, problem, target group, or timeframe).",
        )

    toc_draft = state.get("toc_draft")
    toc_payload = (toc_draft or {}).get("toc") if isinstance(toc_draft, dict) else None
    logframe = state.get("logframe_draft") or state.get("mel")
    indicators = (logframe or {}).get("indicators") if isinstance(logframe, dict) else None

    if not isinstance(toc_draft, dict) or not isinstance(toc_payload, dict):
        checks.append(RuleCheckResult(code="TOC_PRESENT", status="fail", section="toc", detail="ToC draft missing"))
        _add_flaw(
            flaws,
            code="TOC_MISSING",
            severity="high",
            section="toc",
            state=state,
            message="Theory of Change draft is missing.",
            fix_hint="Run architect step and ensure ToC generation succeeds before critic review.",
        )
    else:
        checks.append(RuleCheckResult(code="TOC_PRESENT", status="pass", section="toc"))

    toc_validation = state.get("toc_validation") if isinstance(state.get("toc_validation"), dict) else {}
    if toc_validation:
        if toc_validation.get("valid") is True:
            checks.append(RuleCheckResult(code="TOC_SCHEMA_VALID", status="pass", section="toc"))
        else:
            errors = toc_validation.get("errors") if isinstance(toc_validation.get("errors"), list) else []
            checks.append(
                RuleCheckResult(
                    code="TOC_SCHEMA_VALID",
                    status="fail",
                    section="toc",
                    detail=f"{len(errors)} schema validation errors",
                )
            )
            _add_flaw(
                flaws,
                code="TOC_SCHEMA_INVALID",
                severity="high",
                section="toc",
                state=state,
                message="ToC does not match donor-specific schema contract.",
                fix_hint="Revise architect output to satisfy strategy.get_toc_schema() validation errors.",
            )
    else:
        checks.append(
            RuleCheckResult(
                code="TOC_SCHEMA_VALID",
                status="warn",
                section="toc",
                detail="No toc_validation metadata present",
            )
        )

    apply_donor_specific_toc_checks(
        state=state,
        toc_payload=toc_payload,
        check_fn=lambda **kwargs: _check(checks, **kwargs),
        add_flaw_fn=lambda **kwargs: _add_flaw(flaws, state=state, **kwargs),
    )

    architect_citations = [c for c in _iter_citations(state, stage="architect")]
    if architect_citations:
        claim_level = [c for c in architect_citations if c.get("statement_path")]
        if claim_level:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_CITATIONS",
                    status="pass",
                    section="toc",
                    detail=f"{len(claim_level)} claim-level architect citations",
                )
            )
        else:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_CITATIONS", status="warn", section="toc", detail="No statement_path citations"
                )
            )
            _add_flaw(
                flaws,
                code="TOC_CITATION_TRACE_WEAK",
                severity="medium",
                section="toc",
                state=state,
                message="ToC lacks claim-level citation traceability.",
                fix_hint="Attach architect citations with statement_path to key objectives and assumptions.",
            )
    else:
        checks.append(
            RuleCheckResult(code="TOC_CLAIM_CITATIONS", status="fail", section="toc", detail="No architect citations")
        )
        _add_flaw(
            flaws,
            code="TOC_CITATIONS_MISSING",
            severity="medium",
            section="toc",
            state=state,
            message="No architect citation trace was recorded for the ToC draft.",
            fix_hint="Enable/verify architect citation capture and donor namespace grounding.",
        )

    if isinstance(indicators, list) and indicators:
        checks.append(
            RuleCheckResult(
                code="LOGFRAME_INDICATORS_PRESENT",
                status="pass",
                section="logframe",
                detail=f"{len(indicators)} indicators",
            )
        )
    else:
        checks.append(
            RuleCheckResult(
                code="LOGFRAME_INDICATORS_PRESENT",
                status="fail",
                section="logframe",
                detail="Indicators missing",
            )
        )
        _add_flaw(
            flaws,
            code="LOGFRAME_INDICATORS_MISSING",
            severity="high",
            section="logframe",
            state=state,
            message="LogFrame/MEL indicators are missing.",
            fix_hint="Run MEL specialist and ensure indicator extraction or fallback indicator generation succeeds.",
        )

    mel_citations = [c for c in _iter_citations(state, stage="mel")]
    if mel_citations:
        checks.append(
            RuleCheckResult(
                code="LOGFRAME_CITATIONS_PRESENT",
                status="pass",
                section="logframe",
                detail=f"{len(mel_citations)} MEL citations",
            )
        )
    else:
        checks.append(
            RuleCheckResult(
                code="LOGFRAME_CITATIONS_PRESENT", status="warn", section="logframe", detail="No MEL citations"
            )
        )
        _add_flaw(
            flaws,
            code="LOGFRAME_CITATIONS_MISSING",
            severity="medium",
            section="logframe",
            state=state,
            message="Indicators are not accompanied by citation traceability.",
            fix_hint="Ensure MEL step records citation metadata for retrieved or fallback indicators.",
        )

    severity_penalty = {"high": 2.0, "medium": 1.0, "low": 0.5}
    score = 9.25 - sum(severity_penalty.get(f.severity, 1.0) for f in flaws)
    score = max(0.0, min(10.0, round(score, 2)))

    if flaws:
        top_flaws = flaws[:3]
        instruction_lines = [
            "Address the following issues before finalizing the draft:",
            *[f"- [{f.section}] {f.message}" for f in top_flaws],
        ]
        revision_instructions = "\n".join(instruction_lines)
    else:
        revision_instructions = (
            "Rule-based critic found no fatal issues. Tighten specificity and donor alignment where possible."
        )

    return RuleCriticReport(
        score=score,
        fatal_flaws=flaws,
        checks=checks,
        revision_instructions=revision_instructions,
    )
