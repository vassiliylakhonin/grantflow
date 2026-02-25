from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

from grantflow.swarm.versioning import filter_versions


class CriticFatalFlaw(BaseModel):
    code: str = Field(description="Stable rule/check code")
    severity: str = Field(description="Severity level: low|medium|high")
    section: str = Field(description="Affected section: toc|logframe|general")
    version_id: Optional[str] = Field(default=None, description="Related draft version id, if available")
    message: str = Field(description="Human-readable issue summary")
    fix_hint: Optional[str] = Field(default=None, description="Suggested fix")
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


def _normalized_donor_id(state: Dict[str, Any]) -> str:
    donor = state.get("donor_id") or state.get("donor") or ""
    return str(donor).strip().lower()


def _check(
    checks: List[RuleCheckResult],
    *,
    code: str,
    status: str,
    section: str,
    detail: Optional[str] = None,
) -> None:
    checks.append(RuleCheckResult(code=code, status=status, section=section, detail=detail))


def _donor_specific_toc_checks(
    *,
    state: Dict[str, Any],
    toc_payload: Any,
    checks: List[RuleCheckResult],
    flaws: List[CriticFatalFlaw],
) -> None:
    donor = _normalized_donor_id(state)
    if not isinstance(toc_payload, dict):
        return

    if donor == "usaid":
        dos = toc_payload.get("development_objectives")
        if isinstance(dos, list) and dos:
            _check(checks, code="USAID_DO_PRESENT", status="pass", section="toc", detail=f"{len(dos)} DO(s)")
            ir_count = 0
            output_count = 0
            missing_ir = False
            missing_outputs = False
            for do in dos:
                if not isinstance(do, dict):
                    missing_ir = True
                    continue
                irs = do.get("intermediate_results")
                if not isinstance(irs, list) or not irs:
                    missing_ir = True
                    continue
                ir_count += len(irs)
                for ir in irs:
                    if not isinstance(ir, dict):
                        missing_outputs = True
                        continue
                    outputs = ir.get("outputs")
                    if not isinstance(outputs, list) or not outputs:
                        missing_outputs = True
                        continue
                    output_count += len(outputs)

            if missing_ir:
                _check(checks, code="USAID_IR_HIERARCHY", status="fail", section="toc", detail="One or more DOs missing IRs")
                _add_flaw(
                    flaws,
                    code="USAID_IR_MISSING",
                    severity="high",
                    section="toc",
                    state=state,
                    message="USAID ToC hierarchy is incomplete: each Development Objective should include Intermediate Results.",
                    fix_hint="Populate `development_objectives[].intermediate_results[]` with a clear results cascade.",
                )
            else:
                _check(checks, code="USAID_IR_HIERARCHY", status="pass", section="toc", detail=f"{ir_count} IR(s)")

            if missing_outputs:
                _check(
                    checks,
                    code="USAID_OUTPUT_HIERARCHY",
                    status="fail",
                    section="toc",
                    detail="One or more IRs missing outputs",
                )
                _add_flaw(
                    flaws,
                    code="USAID_OUTPUTS_MISSING",
                    severity="high",
                    section="toc",
                    state=state,
                    message="USAID ToC hierarchy is incomplete: Intermediate Results should include outputs.",
                    fix_hint="Populate `intermediate_results[].outputs[]` under each USAID IR.",
                )
            else:
                _check(checks, code="USAID_OUTPUT_HIERARCHY", status="pass", section="toc", detail=f"{output_count} output(s)")
        else:
            _check(checks, code="USAID_DO_PRESENT", status="fail", section="toc", detail="No development_objectives")
            _add_flaw(
                flaws,
                code="USAID_DO_MISSING",
                severity="high",
                section="toc",
                state=state,
                message="USAID ToC is missing Development Objectives.",
                fix_hint="Add at least one `development_objective` with DO -> IR -> Output hierarchy.",
            )

        assumptions = toc_payload.get("critical_assumptions")
        if isinstance(assumptions, list) and assumptions:
            _check(
                checks,
                code="USAID_CRITICAL_ASSUMPTIONS_PRESENT",
                status="pass",
                section="toc",
                detail=f"{len(assumptions)} assumptions",
            )
        else:
            _check(
                checks, code="USAID_CRITICAL_ASSUMPTIONS_PRESENT", status="warn", section="toc", detail="No critical_assumptions"
            )
            _add_flaw(
                flaws,
                code="USAID_ASSUMPTIONS_MISSING",
                severity="medium",
                section="toc",
                state=state,
                message="USAID ToC should include critical assumptions for the results hierarchy.",
                fix_hint="Add `critical_assumptions` describing external conditions needed for success.",
            )
        return

    if donor == "eu":
        overall = toc_payload.get("overall_objective")
        if isinstance(overall, dict):
            missing = [k for k in ("objective_id", "title", "rationale") if not str(overall.get(k) or "").strip()]
            if not missing:
                _check(checks, code="EU_OVERALL_OBJECTIVE_COMPLETE", status="pass", section="toc")
            else:
                _check(
                    checks,
                    code="EU_OVERALL_OBJECTIVE_COMPLETE",
                    status="fail",
                    section="toc",
                    detail=f"Missing fields: {', '.join(missing)}",
                )
                _add_flaw(
                    flaws,
                    code="EU_INTERVENTION_LOGIC_INCOMPLETE",
                    severity="high",
                    section="toc",
                    state=state,
                    message="EU ToC overall objective is incomplete (ID/title/rationale required).",
                    fix_hint="Populate `overall_objective.objective_id`, `title`, and `rationale`.",
                )
        else:
            _check(checks, code="EU_OVERALL_OBJECTIVE_COMPLETE", status="fail", section="toc", detail="Missing overall_objective")
            _add_flaw(
                flaws,
                code="EU_OVERALL_OBJECTIVE_MISSING",
                severity="high",
                section="toc",
                state=state,
                message="EU ToC is missing `overall_objective`.",
                fix_hint="Provide an EU intervention-logic style `overall_objective` with rationale.",
            )
        return

    if donor == "giz":
        outcomes = toc_payload.get("outcomes")
        if isinstance(outcomes, list) and outcomes:
            _check(checks, code="GIZ_OUTCOMES_PRESENT", status="pass", section="toc", detail=f"{len(outcomes)} outcomes")
            missing_partner_role = False
            for row in outcomes:
                if not isinstance(row, dict) or not str(row.get("partner_role") or "").strip():
                    missing_partner_role = True
                    break
            if missing_partner_role:
                _check(
                    checks,
                    code="GIZ_PARTNER_ROLE_PRESENT",
                    status="fail",
                    section="toc",
                    detail="One or more outcomes missing partner_role",
                )
                _add_flaw(
                    flaws,
                    code="GIZ_PARTNER_ROLE_MISSING",
                    severity="medium",
                    section="toc",
                    state=state,
                    message="GIZ outcomes should identify partner roles.",
                    fix_hint="Populate `outcomes[].partner_role` for technical cooperation implementation responsibility.",
                )
            else:
                _check(checks, code="GIZ_PARTNER_ROLE_PRESENT", status="pass", section="toc")
        else:
            _check(checks, code="GIZ_OUTCOMES_PRESENT", status="fail", section="toc", detail="No outcomes")
            _add_flaw(
                flaws,
                code="GIZ_OUTCOMES_MISSING",
                severity="high",
                section="toc",
                state=state,
                message="GIZ ToC is missing outcomes.",
                fix_hint="Add practical outcomes aligned with technical cooperation objectives and partners.",
            )

        sustainability = toc_payload.get("sustainability_factors")
        if isinstance(sustainability, list) and sustainability:
            _check(
                checks,
                code="GIZ_SUSTAINABILITY_FACTORS_PRESENT",
                status="pass",
                section="toc",
                detail=f"{len(sustainability)} factors",
            )
        else:
            _check(
                checks, code="GIZ_SUSTAINABILITY_FACTORS_PRESENT", status="warn", section="toc", detail="No sustainability_factors"
            )
            _add_flaw(
                flaws,
                code="GIZ_SUSTAINABILITY_FACTORS_MISSING",
                severity="medium",
                section="toc",
                state=state,
                message="GIZ ToC should include sustainability factors.",
                fix_hint="Add `sustainability_factors` covering institutionalization and continuation after project support.",
            )
        return

    if donor in {"state_department", "us_state_department", "us_state_department_guidance"}:
        for key, code, msg, hint in [
            ("strategic_context", "STATE_STRATEGIC_CONTEXT_PRESENT", "State Department ToC should include strategic context.", "Populate `strategic_context` with country/political/program context."),
        ]:
            if str(toc_payload.get(key) or "").strip():
                _check(checks, code=code, status="pass", section="toc")
            else:
                _check(checks, code=code, status="fail", section="toc", detail=f"Missing {key}")
                _add_flaw(
                    flaws,
                    code=f"{code}_MISSING",
                    severity="high",
                    section="toc",
                    state=state,
                    message=msg,
                    fix_hint=hint,
                )
        for key, code, label in [
            ("stakeholder_map", "STATE_STAKEHOLDER_MAP_PRESENT", "stakeholder_map"),
            ("risk_mitigation", "STATE_RISK_MITIGATION_PRESENT", "risk_mitigation"),
        ]:
            rows = toc_payload.get(key)
            if isinstance(rows, list) and rows:
                _check(checks, code=code, status="pass", section="toc", detail=f"{len(rows)} {label} entries")
            else:
                _check(checks, code=code, status="warn", section="toc", detail=f"No {label}")
                _add_flaw(
                    flaws,
                    code=f"{code}_MISSING",
                    severity="medium",
                    section="toc",
                    state=state,
                    message=f"State Department ToC should include {label.replace('_', ' ')}.",
                    fix_hint=f"Add `{key}` entries for stakeholder logic and risk mitigation planning.",
                )
        return

    if donor == "worldbank":
        objectives = toc_payload.get("objectives")
        if isinstance(objectives, list) and objectives:
            _check(checks, code="WB_OBJECTIVES_PRESENT", status="pass", section="toc", detail=f"{len(objectives)} objectives")
            incomplete = False
            for obj in objectives:
                if not isinstance(obj, dict):
                    incomplete = True
                    break
                if not all(str(obj.get(k) or "").strip() for k in ("objective_id", "title", "description")):
                    incomplete = True
                    break
            if incomplete:
                _check(checks, code="WB_OBJECTIVES_COMPLETE", status="fail", section="toc", detail="Incomplete objective fields")
                _add_flaw(
                    flaws,
                    code="WB_OBJECTIVE_FIELDS_INCOMPLETE",
                    severity="high",
                    section="toc",
                    state=state,
                    message="World Bank ToC objectives should include objective_id, title, and description.",
                    fix_hint="Complete fields for each `objectives[]` entry in the World Bank ToC schema.",
                )
            else:
                _check(checks, code="WB_OBJECTIVES_COMPLETE", status="pass", section="toc")
        else:
            _check(checks, code="WB_OBJECTIVES_PRESENT", status="fail", section="toc", detail="No objectives")
            _add_flaw(
                flaws,
                code="WB_OBJECTIVES_MISSING",
                severity="high",
                section="toc",
                state=state,
                message="World Bank ToC is missing objectives.",
                fix_hint="Add at least one objective with ID, title, and description.",
            )



def evaluate_rule_based_critic(state: Dict[str, Any]) -> RuleCriticReport:
    checks: List[RuleCheckResult] = []
    flaws: List[CriticFatalFlaw] = []

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

    _donor_specific_toc_checks(state=state, toc_payload=toc_payload, checks=checks, flaws=flaws)

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
