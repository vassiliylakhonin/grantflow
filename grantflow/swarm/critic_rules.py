from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, cast

from pydantic import BaseModel, Field

from grantflow.core.evaluation_rfq import (
    EVALUATION_RFQ_PROPOSAL_MODE,
    KATCH_EVALUATION_RFQ_PROFILE,
)
from grantflow.swarm.critic_donor_policy import apply_donor_specific_toc_checks
from grantflow.swarm.citations import citation_traceability_status
from grantflow.swarm.state_contract import state_input_context
from grantflow.swarm.versioning import filter_versions

BASELINE_TARGET_PLACEHOLDER_VALUES = {
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

TOC_TEXT_PLACEHOLDER_VALUES = {
    "",
    "tbd",
    "to be determined",
    "placeholder",
    "lorem ipsum",
    "todo",
    "n/a",
    "na",
    "unknown",
    "-",
    "--",
    "none",
    "null",
}
TOC_TEXT_PLACEHOLDER_SNIPPETS = (
    "tbd",
    "to be determined",
    "placeholder",
    "lorem ipsum",
    "todo",
    "[insert",
    "(insert",
    "fill in",
)
TOC_CLAIM_TEXT_KEYS = {
    "project_goal",
    "project_development_objective",
    "program_goal",
    "programme_objective",
    "overall_objective",
    "brief",
    "summary",
    "problem_statement",
    "description",
    "title",
    "assumption",
    "assumptions",
    "critical_assumptions",
}
TOC_REPETITION_MIN_TEXT_LEN = 40
TOC_REPETITION_WARN_MAX_REPEAT_COUNT = 3
TOC_REPETITION_WARN_RATIO_THRESHOLD = 0.5


def _critic_donor_id(state: Dict[str, Any]) -> str:
    raw = state.get("donor_id") or state.get("donor") or ""
    return str(raw).strip().lower()


def _donor_review_package_phrase(state: Dict[str, Any]) -> str:
    donor = _critic_donor_id(state)
    return {
        "usaid": "USAID results hierarchy and monitoring package",
        "eu": "EU intervention logic and verification package",
        "worldbank": "World Bank results framework and PDO package",
        "giz": "GIZ technical cooperation results package",
        "state_department": "State Department program logic and risk package",
        "us_state_department": "State Department program logic and risk package",
        "un_agencies": "UN results framework and verification package",
    }.get(donor, "donor review package")


def _donor_grounding_phrase(state: Dict[str, Any]) -> str:
    donor = _critic_donor_id(state)
    return {
        "usaid": "results hierarchy evidence and PMP references",
        "eu": "intervention-logic evidence and means-of-verification references",
        "worldbank": "results-framework evidence and ISR/PDO references",
        "giz": "delivery evidence and sustainability references",
        "state_department": "program evidence and partner-risk references",
        "us_state_department": "program evidence and partner-risk references",
        "un_agencies": "results framework evidence and verification references",
    }.get(donor, "evidence references")


def _donor_measurement_phrase(state: Dict[str, Any]) -> str:
    donor = _critic_donor_id(state)
    return {
        "usaid": "PMP-style review",
        "eu": "EU intervention-logic review",
        "worldbank": "results-framework and ISR-style review",
        "giz": "GIZ delivery and sustainability review",
        "state_department": "State Department delivery and risk review",
        "us_state_department": "State Department delivery and risk review",
        "un_agencies": "UN results monitoring and reporting",
    }.get(donor, "review")


def _donor_schema_phrase(state: Dict[str, Any]) -> str:
    donor = _critic_donor_id(state)
    return {
        "usaid": "USAID results hierarchy, assumptions, and monitoring structure",
        "eu": "EU intervention-logic structure, objective hierarchy, and verification narrative",
        "worldbank": "World Bank PDO, objective hierarchy, and results-framework structure",
        "giz": "GIZ outcome, partner-role, and sustainability structure",
        "state_department": "State Department strategic context, stakeholder, and risk structure",
        "us_state_department": "State Department strategic context, stakeholder, and risk structure",
        "un_agencies": "UN objective, outcome, and verification structure",
    }.get(donor, "donor schema and review structure")


def _proposal_mode(state: Dict[str, Any], toc_payload: Any) -> str:
    if isinstance(toc_payload, dict):
        mode = str(toc_payload.get("proposal_mode") or "").strip().lower()
        if mode:
            return mode
    return str(state_input_context(state).get("proposal_mode") or "").strip().lower()


def _rfq_profile(state: Dict[str, Any], toc_payload: Any) -> str:
    if isinstance(toc_payload, dict):
        profile = str(toc_payload.get("rfq_profile") or "").strip().lower()
        if profile:
            return profile
    return str(state_input_context(state).get("rfq_profile") or "").strip().lower()


def _add_katch_evaluation_rfq_checks(
    *,
    state: Dict[str, Any],
    toc_payload: Dict[str, Any],
    check_fn: Any,
    add_flaw_fn: Any,
) -> None:
    scalar_requirements = [
        (
            "KATCH_ORGANIZATION_INFORMATION_PRESENT",
            "organization_information",
            "Organization information is missing, so the technical proposal is incomplete for KATCH RFQ review.",
            "Add organization identity, registration, legal status, and audited-financial attachment readiness for the technical proposal file.",
        ),
        (
            "KATCH_TECHNICAL_APPROACH_PRESENT",
            "technical_approach_summary",
            "Technical approach and methodology narrative is incomplete for KATCH RFQ review.",
            "Describe the proposed approaches, document review process, methods, analytical approach, risks, limitations, and human-subject safeguards in a reviewer-ready technical narrative.",
        ),
        (
            "KATCH_SAMPLING_PLAN_PRESENT",
            "sampling_plan",
            "Sampling plan is missing, so the RFQ response does not yet show how respondent groups will be covered.",
            "Add a sampling plan covering stakeholder groups, beneficiary coverage, and the rationale for respondent selection during fieldwork.",
        ),
        (
            "KATCH_LOE_PRESENT",
            "level_of_effort_summary",
            "Level of effort summary is missing, leaving the KATCH technical proposal weak on staffing realism and phase planning.",
            "Add an activity-based level of effort summary showing person-days by role and phase for engagement, fieldwork, analysis, and reporting.",
        ),
        (
            "KATCH_PAST_PERFORMANCE_PRESENT",
            "technical_experience_summary",
            "Past performance and technical experience summary is missing, so reviewer confidence in comparable evaluation experience stays weak.",
            "Add recent comparable evaluation assignments, donor-relevant technical experience, and verifiable reference context.",
        ),
        (
            "KATCH_SAMPLE_OUTPUTS_PRESENT",
            "sample_outputs_summary",
            "Sample technical outputs are not referenced, so the KATCH submission does not yet evidence comparable report quality.",
            "Reference annexed sample evaluation outputs or report examples that show similar end-line or final-assessment work.",
        ),
        (
            "KATCH_FINANCIAL_SUMMARY_PRESENT",
            "financial_summary",
            "Financial proposal companion summary is missing, so the technical package does not yet explain how pricing aligns with scope and deliverables.",
            "Add a short financial companion summary explaining how staffing, fieldwork, analysis, and reporting costs align to the technical work plan.",
        ),
    ]
    for code, field_name, message, fix_hint in scalar_requirements:
        value = str(toc_payload.get(field_name) or "").strip()
        if value:
            check_fn(code=code, status="pass", section="toc")
        else:
            check_fn(code=code, status="fail", section="toc", detail=f"Missing {field_name}")
            add_flaw_fn(code=code, severity="high", section="toc", message=message, fix_hint=fix_hint)

    methodology_components = toc_payload.get("methodology_components")
    if isinstance(methodology_components, list) and len([m for m in methodology_components if isinstance(m, dict)]) >= 4:
        check_fn(
            code="KATCH_METHOD_COMPONENTS_COMPLETE",
            status="pass",
            section="toc",
            detail=f"{len(methodology_components)} method components",
        )
    else:
        check_fn(
            code="KATCH_METHOD_COMPONENTS_COMPLETE",
            status="fail",
            section="toc",
            detail="Need outcome harvesting, social media analysis, KIIs/FGDs, and beneficiary survey coverage",
        )
        add_flaw_fn(
            code="KATCH_METHOD_COMPONENTS_INCOMPLETE",
            severity="high",
            section="toc",
            message="KATCH methodology components are incomplete, so the technical proposal does not yet cover the expected mixed-method evaluation design.",
            fix_hint="Include reviewer-ready method components for outcome harvesting, social media analysis, KIIs/FGDs, beneficiary survey coverage, and the related evidence sources.",
        )

    ethical_considerations = toc_payload.get("ethical_considerations")
    if isinstance(ethical_considerations, list) and ethical_considerations:
        check_fn(
            code="KATCH_ETHICS_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(ethical_considerations)} ethics item(s)",
        )
    else:
        check_fn(code="KATCH_ETHICS_PRESENT", status="fail", section="toc", detail="No ethical_considerations")
        add_flaw_fn(
            code="KATCH_ETHICS_MISSING",
            severity="high",
            section="toc",
            message="KATCH ethics and do-no-harm safeguards are missing, leaving the RFQ response weak on confidentiality, consent, and trauma-informed practice.",
            fix_hint="Add ethical considerations covering informed consent, confidentiality, secure data handling, do-no-harm, and trauma-informed interview safeguards.",
        )

    team_composition = toc_payload.get("team_composition")
    if isinstance(team_composition, list) and len([r for r in team_composition if isinstance(r, dict)]) >= 2:
        check_fn(code="KATCH_TEAM_COMPOSITION_PRESENT", status="pass", section="toc", detail=f"{len(team_composition)} role(s)")
    else:
        check_fn(code="KATCH_TEAM_COMPOSITION_PRESENT", status="fail", section="toc", detail="Need at least team lead + evaluation expert")
        add_flaw_fn(
            code="KATCH_TEAM_COMPOSITION_MISSING",
            severity="high",
            section="toc",
            message="KATCH team composition is incomplete, so reviewer confidence in delivery and evaluation leadership is still weak.",
            fix_hint="List at least a Team Leader/Evaluation Specialist and an Evaluation Expert/Analyst with clear responsibilities aligned to the RFQ.",
        )

    key_personnel = toc_payload.get("key_personnel") or []
    ready_personnel = [
        row
        for row in key_personnel
        if isinstance(row, dict)
        and str(row.get("name") or "").strip()
        and str(row.get("role") or "").strip()
        and str(row.get("qualifications") or "").strip()
        and str(row.get("cv_status") or "").strip()
    ]
    if len(ready_personnel) >= 2:
        check_fn(
            code="KATCH_KEY_PERSONNEL_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(ready_personnel)} staffed row(s)",
        )
    else:
        check_fn(
            code="KATCH_KEY_PERSONNEL_PRESENT",
            status="fail",
            section="toc",
            detail="Need named or placeholder key personnel rows with qualifications and CV status",
        )
        add_flaw_fn(
            code="KATCH_KEY_PERSONNEL_MISSING",
            severity="high",
            section="toc",
            message="KATCH key personnel packaging is incomplete, so reviewers cannot verify staffing depth, qualifications, and CV readiness for the assignment.",
            fix_hint="Add a key personnel table with named or placeholder staff, role, qualifications, indicative level of effort, and CV attachment status.",
        )

    cost_structure = toc_payload.get("cost_structure") or []
    ready_cost_rows = [
        row
        for row in cost_structure
        if isinstance(row, dict)
        and str(row.get("cost_bucket") or "").strip()
        and str(row.get("basis") or "").strip()
        and str(row.get("estimate") or "").strip()
    ]
    if len(ready_cost_rows) >= 3:
        check_fn(
            code="KATCH_COST_STRUCTURE_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(ready_cost_rows)} cost row(s)",
        )
    else:
        check_fn(
            code="KATCH_COST_STRUCTURE_PRESENT",
            status="fail",
            section="toc",
            detail="Need structured cost buckets linked to staffing, fieldwork, analysis, and reporting",
        )
        add_flaw_fn(
            code="KATCH_COST_STRUCTURE_MISSING",
            severity="medium",
            section="toc",
            message="KATCH cost structure is incomplete, so the financial companion is weak on role-based pricing logic and major delivery cost buckets.",
            fix_hint="Add cost buckets for professional fees, fieldwork/travel, data collection/analysis, and reporting/workshop delivery with short pricing notes.",
        )

    pricing_assumptions = toc_payload.get("pricing_assumptions")
    if isinstance(pricing_assumptions, list) and len([item for item in pricing_assumptions if str(item).strip()]) >= 2:
        check_fn(
            code="KATCH_PRICING_ASSUMPTIONS_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(pricing_assumptions)} pricing assumption(s)",
        )
    else:
        check_fn(
            code="KATCH_PRICING_ASSUMPTIONS_PRESENT",
            status="warn",
            section="toc",
            detail="Limited pricing assumption detail",
        )
        add_flaw_fn(
            code="KATCH_PRICING_ASSUMPTIONS_WEAK",
            severity="medium",
            section="toc",
            message="KATCH pricing assumptions are underspecified, so reviewers cannot quickly understand tax, currency, fieldwork, and reimbursable-cost treatment.",
            fix_hint="State the main pricing assumptions, including staffing basis, fieldwork/travel assumptions, and treatment of taxes or reimbursable costs.",
        )

    payment_schedule = str(toc_payload.get("payment_schedule_summary") or "").strip()
    if payment_schedule:
        check_fn(code="KATCH_PAYMENT_SCHEDULE_PRESENT", status="pass", section="toc")
    else:
        check_fn(code="KATCH_PAYMENT_SCHEDULE_PRESENT", status="warn", section="toc", detail="No payment_schedule_summary")
        add_flaw_fn(
            code="KATCH_PAYMENT_SCHEDULE_WEAK",
            severity="low",
            section="toc",
            message="KATCH payment schedule is not summarized, so the financial companion is weaker on milestone-based invoicing logic.",
            fix_hint="Add a short payment schedule summary tied to inception, fieldwork, draft report, and final submission milestones.",
        )

    submission_package_checklist = toc_payload.get("submission_package_checklist") or []
    ready_submission_items = [
        row
        for row in submission_package_checklist
        if isinstance(row, dict)
        and str(row.get("artifact") or "").strip()
        and str(row.get("owner") or "").strip()
        and str(row.get("status") or "").strip()
    ]
    if len(ready_submission_items) >= 5:
        check_fn(
            code="KATCH_SUBMISSION_PACKAGE_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(ready_submission_items)} submission item(s)",
        )
    else:
        check_fn(
            code="KATCH_SUBMISSION_PACKAGE_PRESENT",
            status="fail",
            section="toc",
            detail="Need a package-level checklist for the technical response and supporting annexes",
        )
        add_flaw_fn(
            code="KATCH_SUBMISSION_PACKAGE_MISSING",
            severity="medium",
            section="toc",
            message="KATCH submission package checklist is incomplete, so the team cannot reliably verify that the final technical package and annexes are assembled for submission.",
            fix_hint="Add a submission package checklist naming each required artifact, owner, status, and remaining packaging notes before submission.",
        )

    workplan_summary = toc_payload.get("workplan_summary")
    if isinstance(workplan_summary, list) and workplan_summary:
        check_fn(code="KATCH_WORKPLAN_PRESENT", status="pass", section="toc", detail=f"{len(workplan_summary)} workplan phase(s)")
    else:
        check_fn(code="KATCH_WORKPLAN_PRESENT", status="fail", section="toc", detail="No workplan_summary")
        add_flaw_fn(
            code="KATCH_WORKPLAN_MISSING",
            severity="medium",
            section="toc",
            message="KATCH work plan is missing, so the technical proposal does not yet show a credible phase structure for engagement, fieldwork, and reporting.",
            fix_hint="Add an activity-based work plan or Gantt-style phase summary that covers engagement, data collection, analysis, workshop, and final reporting.",
        )

    deliverables = toc_payload.get("deliverables")
    deliverable_titles = [
        str(row.get("deliverable") or "").strip().lower()
        for row in deliverables
        if isinstance(deliverables, list) and isinstance(row, dict)
    ]
    required_tokens = ("inception", "bi-week", "workshop", "draft evaluation report", "final evaluation report")
    if deliverable_titles and all(any(token in title for title in deliverable_titles) for token in required_tokens):
        check_fn(code="KATCH_DELIVERABLE_PLAN_COMPLETE", status="pass", section="toc", detail=f"{len(deliverable_titles)} deliverable(s)")
    else:
        check_fn(code="KATCH_DELIVERABLE_PLAN_COMPLETE", status="fail", section="toc", detail="Missing one or more required RFQ deliverables")
        add_flaw_fn(
            code="KATCH_DELIVERABLE_PLAN_INCOMPLETE",
            severity="high",
            section="toc",
            message="KATCH deliverable plan is incomplete, so the submission does not yet cover the RFQ milestone package and reporting cadence.",
            fix_hint="Cover inception report, bi-weekly updates, validation workshop, draft evaluation report, stand-alone brief, and final evaluation report in the deliverable plan.",
        )

    annex_readiness = toc_payload.get("annex_readiness")
    if isinstance(annex_readiness, list) and len([item for item in annex_readiness if str(item).strip()]) >= 4:
        check_fn(code="KATCH_ANNEX_READINESS_PRESENT", status="pass", section="toc", detail=f"{len(annex_readiness)} annex item(s)")
    else:
        check_fn(code="KATCH_ANNEX_READINESS_PRESENT", status="warn", section="toc", detail="Limited annex_readiness detail")
        add_flaw_fn(
            code="KATCH_ANNEX_READINESS_WEAK",
            severity="medium",
            section="toc",
            message="KATCH annex readiness is underspecified, so the technical package is still weak on attachments reviewers expect to see alongside the narrative.",
            fix_hint="List the key supporting annexes: registration/audit evidence, CVs, sample outputs, work plan, and level-of-effort matrix.",
        )

    compliance_matrix = toc_payload.get("compliance_matrix") or []
    ready_rows = [
        row
        for row in compliance_matrix
        if isinstance(compliance_matrix, list)
        and isinstance(row, dict)
        and str(row.get("requirement") or "").strip()
        and str(row.get("response_section") or "").strip()
        and str(row.get("evidence") or "").strip()
    ]
    if len(ready_rows) >= 5:
        check_fn(
            code="KATCH_COMPLIANCE_MATRIX_PRESENT",
            status="pass",
            section="toc",
            detail=f"{len(ready_rows)} compliance row(s)",
        )
    else:
        check_fn(
            code="KATCH_COMPLIANCE_MATRIX_PRESENT",
            status="fail",
            section="toc",
            detail="Need a requirement-to-response compliance matrix for the RFQ technical package",
        )
        add_flaw_fn(
            code="KATCH_COMPLIANCE_MATRIX_MISSING",
            severity="high",
            section="toc",
            message="KATCH compliance mapping is incomplete, so reviewers cannot quickly verify where each RFQ requirement is covered in the technical package.",
            fix_hint="Add a compliance matrix that maps each major RFQ requirement to the response section, supporting evidence, and attachment readiness state.",
        )


class CriticFatalFlaw(BaseModel):
    id: Optional[str] = Field(default=None, description="Canonical finding identifier within a job")
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
    updated_at: Optional[str] = Field(default=None, description="Timestamp when finding was last updated")
    updated_by: Optional[str] = Field(default=None, description="Actor who last updated finding status")
    acknowledged_at: Optional[str] = Field(default=None, description="Timestamp when acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="Actor who acknowledged finding")
    resolved_at: Optional[str] = Field(default=None, description="Timestamp when resolved")
    resolved_by: Optional[str] = Field(default=None, description="Actor who resolved finding")
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


def _estimate_key_toc_claim_count(toc_payload: Any) -> int:
    if not isinstance(toc_payload, dict):
        return 1
    count = 0
    for field_name in (
        "project_goal",
        "project_development_objective",
        "program_goal",
        "programme_objective",
        "overall_objective",
    ):
        value = toc_payload.get(field_name)
        if isinstance(value, dict) and value:
            count += 1
        elif isinstance(value, str) and value.strip():
            count += 1
    for list_field in (
        "development_objectives",
        "specific_objectives",
        "expected_outcomes",
        "objectives",
        "results_chain",
        "outcomes",
    ):
        value = toc_payload.get(list_field)
        if not isinstance(value, list):
            continue
        count += len([row for row in value if isinstance(row, (dict, str)) and bool(row)])
    return max(1, min(16, count))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _is_placeholder_baseline_target(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if text in BASELINE_TARGET_PLACEHOLDER_VALUES:
        return True
    if "tbd" in text:
        return True
    if "to be determined" in text:
        return True
    return False


def _is_placeholder_toc_text(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if text in TOC_TEXT_PLACEHOLDER_VALUES:
        return True
    if any(snippet in text for snippet in TOC_TEXT_PLACEHOLDER_SNIPPETS):
        return True
    if re.search(r"\b(tbd|todo)\b", text):
        return True
    return False


def _collect_toc_claim_text_scalars(payload: Any, *, max_items: int = 240) -> list[str]:
    out: list[str] = []

    def walk(node: Any, parent_key: Optional[str] = None) -> None:
        if len(out) >= max_items:
            return
        if isinstance(node, str):
            text = node.strip()
            key = str(parent_key or "").strip().lower()
            if text and key in TOC_CLAIM_TEXT_KEYS:
                out.append(text)
            return
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, str(key or "").strip().lower())
                if len(out) >= max_items:
                    return
            return
        if isinstance(node, list):
            for item in node:
                walk(item, parent_key)
                if len(out) >= max_items:
                    return

    walk(payload)
    return out


def _toc_repetition_key(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < TOC_REPETITION_MIN_TEXT_LEN or " " not in text:
        return None
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < TOC_REPETITION_MIN_TEXT_LEN:
        return None
    return text


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
            message=f"Theory of Change draft is missing, so the {_donor_review_package_phrase(state)} cannot yet be reviewed.",
            fix_hint=(
                "Run architect step and ensure ToC generation succeeds before critic review so the draft can be "
                f"checked against the {_donor_schema_phrase(state)}."
            ),
        )
    else:
        checks.append(RuleCheckResult(code="TOC_PRESENT", status="pass", section="toc"))
        toc_text_values = _collect_toc_claim_text_scalars(toc_payload)
        placeholder_text_values = [value for value in toc_text_values if _is_placeholder_toc_text(value)]
        if placeholder_text_values:
            placeholder_ratio = _safe_ratio(len(placeholder_text_values), len(toc_text_values))
            detail = (
                f"{len(placeholder_text_values)}/{len(toc_text_values)} ToC text fields look like placeholders "
                f"(ratio={placeholder_ratio:.0%})"
            )
            if placeholder_ratio >= 0.4 or len(placeholder_text_values) >= 3:
                checks.append(
                    RuleCheckResult(
                        code="TOC_TEXT_COMPLETENESS",
                        status="fail",
                        section="toc",
                        detail=detail,
                    )
                )
                _add_flaw(
                    flaws,
                    code="TOC_PLACEHOLDER_CONTENT_CRITICAL",
                    severity="high",
                    section="toc",
                    state=state,
                    message=(
                        "Theory of Change text is still dominated by placeholder language, so reviewers cannot assess "
                        f"the real objective, outcome, and assumption logic in the {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Replace placeholder text (TBD/TODO/placeholder) with section-specific objective, outcome, "
                        f"and assumption statements before the next { _donor_measurement_phrase(state) } pass."
                    ),
                )
            else:
                checks.append(
                    RuleCheckResult(
                        code="TOC_TEXT_COMPLETENESS",
                        status="warn",
                        section="toc",
                        detail=detail,
                    )
                )
                _add_flaw(
                    flaws,
                    code="TOC_PLACEHOLDER_CONTENT",
                    severity="low",
                    section="toc",
                    state=state,
                    message=(
                        "Theory of Change still contains placeholder text in reviewer-visible sections of the "
                        f"{_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Replace remaining placeholder text (TBD/TODO/placeholder) with concrete, reviewer-facing "
                        "statements before the next pass."
                    ),
                )
        else:
            checks.append(
                RuleCheckResult(
                    code="TOC_TEXT_COMPLETENESS",
                    status="pass",
                    section="toc",
                    detail="No placeholder text detected in ToC fields",
                )
            )
        repetition_groups: Dict[str, Dict[str, Any]] = {}
        repetition_candidates = 0
        for value in toc_text_values:
            key = _toc_repetition_key(value)
            if not key:
                continue
            repetition_candidates += 1
            row = repetition_groups.get(key)
            if row is None:
                repetition_groups[key] = {"count": 1, "sample": str(value).strip()}
            else:
                row["count"] = int(row.get("count") or 0) + 1
        repeated_groups = [row for row in repetition_groups.values() if int(row.get("count") or 0) >= 2]
        repeated_group_count = len(repeated_groups)
        repeated_occurrence_count = sum(int(row.get("count") or 0) for row in repeated_groups)
        max_repeat_count = max((int(row.get("count") or 0) for row in repeated_groups), default=0)
        repeated_ratio = _safe_ratio(repeated_occurrence_count, repetition_candidates) if repetition_candidates else 0.0
        if repeated_group_count and (
            max_repeat_count >= TOC_REPETITION_WARN_MAX_REPEAT_COUNT
            or repeated_ratio >= TOC_REPETITION_WARN_RATIO_THRESHOLD
        ):
            repeated_samples = sorted(
                [
                    str(row.get("sample") or "").strip()
                    for row in repeated_groups
                    if str(row.get("sample") or "").strip()
                ],
                key=len,
                reverse=True,
            )
            sample = (repeated_samples[0][:96] + "...") if repeated_samples else ""
            detail = (
                f"repeated_groups={repeated_group_count}; repeated_occurrences={repeated_occurrence_count}; "
                f"max_repeat_count={max_repeat_count}; ratio={repeated_ratio:.0%}; sample={sample or '-'}"
            )
            checks.append(
                RuleCheckResult(
                    code="TOC_NARRATIVE_DIVERSITY",
                    status="warn",
                    section="toc",
                    detail=detail,
                )
            )
            _add_flaw(
                flaws,
                code="TOC_BOILERPLATE_REPETITION",
                severity="low",
                section="toc",
                state=state,
                message=(
                    "Theory of Change repeats boilerplate narrative across multiple sections, which weakens reviewer "
                    f"confidence in the causal logic of the {_donor_review_package_phrase(state)}."
                ),
                fix_hint=(
                    "Replace repeated objective/result text with section-specific, evidence-grounded wording so each "
                    "result line reads as a distinct causal step for donor review."
                ),
            )
        else:
            checks.append(
                RuleCheckResult(
                    code="TOC_NARRATIVE_DIVERSITY",
                    status="pass",
                    section="toc",
                    detail=(
                        "No significant repeated boilerplate narrative detected"
                        if repetition_candidates
                        else "Not enough narrative text to evaluate repetition"
                    ),
                )
            )

    raw_toc_validation = state.get("toc_validation")
    toc_validation: Dict[str, Any] = (
        cast(Dict[str, Any], raw_toc_validation) if isinstance(raw_toc_validation, dict) else {}
    )
    if toc_validation:
        if toc_validation.get("valid") is True:
            checks.append(RuleCheckResult(code="TOC_SCHEMA_VALID", status="pass", section="toc"))
        else:
            raw_errors = toc_validation.get("errors")
            errors: List[Any] = list(raw_errors) if isinstance(raw_errors, list) else []
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
                message=(
                    "ToC does not match the donor-specific schema contract, so the draft is not yet reviewable as a "
                    f"{_donor_review_package_phrase(state)}."
                ),
                fix_hint=(
                    "Revise architect output to satisfy `strategy.get_toc_schema()` validation errors and restore the "
                    f"{_donor_schema_phrase(state)}."
                ),
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

    if (
        _proposal_mode(state, toc_payload) == EVALUATION_RFQ_PROPOSAL_MODE
        and _rfq_profile(state, toc_payload) == KATCH_EVALUATION_RFQ_PROFILE
    ):
        _add_katch_evaluation_rfq_checks(
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
                message=(
                    "ToC lacks claim-level citation traceability for key objectives and assumptions, so reviewers "
                    f"cannot follow the {_donor_grounding_phrase(state)} claim by claim."
                ),
                fix_hint=(
                    "Attach architect citations with `statement_path` to key objectives, outcomes, and assumptions so "
                    "reviewers can trace each claim directly."
                ),
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
            message=(
                "No architect citation trace was recorded for the ToC draft, leaving reviewers without evidence "
                f"anchors for the {_donor_review_package_phrase(state)}."
            ),
            fix_hint=(
                "Enable or verify architect citation capture and donor namespace grounding before the next review "
                "cycle."
            ),
        )

    architect_claim_citations = [
        c
        for c in architect_citations
        if str(c.get("used_for") or "") == "toc_claim" and str(c.get("statement_path") or "").strip()
    ]
    architect_claim_paths = {
        str(c.get("statement_path") or "").strip()
        for c in architect_claim_citations
        if str(c.get("statement_path") or "").strip() and str(c.get("statement_path") or "").strip() != "toc"
    }
    expected_key_claims = _estimate_key_toc_claim_count(toc_payload)
    observed_claim_coverage_ratio = _safe_ratio(len(architect_claim_paths), expected_key_claims)
    raw_toc_generation_meta = state.get("toc_generation_meta")
    toc_generation_meta: Dict[str, Any] = (
        cast(Dict[str, Any], raw_toc_generation_meta) if isinstance(raw_toc_generation_meta, dict) else {}
    )
    raw_claim_coverage_meta = toc_generation_meta.get("claim_coverage")
    claim_coverage_meta: Dict[str, Any] = (
        cast(Dict[str, Any], raw_claim_coverage_meta) if isinstance(raw_claim_coverage_meta, dict) else {}
    )
    raw_key_claim_coverage_ratio = claim_coverage_meta.get("key_claim_coverage_ratio")
    if raw_key_claim_coverage_ratio is None:
        key_claim_coverage_ratio = observed_claim_coverage_ratio
    else:
        try:
            key_claim_coverage_ratio = float(raw_key_claim_coverage_ratio)
        except (TypeError, ValueError):
            key_claim_coverage_ratio = observed_claim_coverage_ratio
    raw_fallback_claim_ratio = claim_coverage_meta.get("fallback_claim_ratio")
    if raw_fallback_claim_ratio is None:
        fallback_claim_ratio = _safe_ratio(
            sum(1 for c in architect_claim_citations if str(c.get("citation_type") or "") == "fallback_namespace"),
            len(architect_claim_citations),
        )
    else:
        try:
            fallback_claim_ratio = float(raw_fallback_claim_ratio)
        except (TypeError, ValueError):
            fallback_claim_ratio = _safe_ratio(
                sum(1 for c in architect_claim_citations if str(c.get("citation_type") or "") == "fallback_namespace"),
                len(architect_claim_citations),
            )
    architect_rag_enabled = bool(state.get("architect_rag_enabled", True))

    if architect_claim_citations:
        coverage_detail = (
            f"coverage={key_claim_coverage_ratio:.0%} "
            f"({len(architect_claim_paths)}/{expected_key_claims} key claim paths)"
        )
        if key_claim_coverage_ratio >= 0.8:
            checks.append(
                RuleCheckResult(code="TOC_KEY_CLAIM_COVERAGE", status="pass", section="toc", detail=coverage_detail)
            )
        elif key_claim_coverage_ratio >= 0.5:
            checks.append(
                RuleCheckResult(code="TOC_KEY_CLAIM_COVERAGE", status="warn", section="toc", detail=coverage_detail)
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_KEY_CLAIM_COVERAGE_LOW",
                    severity="medium",
                    section="toc",
                    state=state,
                    message=(
                        "Architect citations do not cover enough key ToC objectives/results for reviewer confidence "
                        f"in the {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Increase claim-level grounding so key objectives/results have explicit `statement_path` "
                        "citations."
                    ),
                )
        else:
            checks.append(
                RuleCheckResult(code="TOC_KEY_CLAIM_COVERAGE", status="fail", section="toc", detail=coverage_detail)
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_KEY_CLAIM_COVERAGE_CRITICAL",
                    severity="high",
                    section="toc",
                    state=state,
                    message=(
                        "Architect claim coverage is too low for key ToC objectives/results, so the draft is not "
                        f"yet reviewable as a {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Ground each key objective/result statement with retrieved evidence and `statement_path` "
                        "citations."
                    ),
                )
    else:
        checks.append(
            RuleCheckResult(
                code="TOC_KEY_CLAIM_COVERAGE",
                status="warn",
                section="toc",
                detail="No architect toc_claim citations available for key-claim coverage check",
            )
        )

    if len(architect_claim_citations) >= 3:
        fallback_detail = (
            f"fallback_claim_ratio={fallback_claim_ratio:.0%} "
            f"({sum(1 for c in architect_claim_citations if str(c.get('citation_type') or '') == 'fallback_namespace')}/"
            f"{len(architect_claim_citations)})"
        )
        if fallback_claim_ratio < 0.5:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_GROUNDING_BALANCE", status="pass", section="toc", detail=fallback_detail
                )
            )
        elif fallback_claim_ratio < 0.8:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_GROUNDING_BALANCE", status="warn", section="toc", detail=fallback_detail
                )
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_GROUNDING_WEAK",
                    severity="medium",
                    section="toc",
                    state=state,
                    message=(
                        "Fallback namespace citations dominate too many architect claims, so the ToC is only weakly "
                        f"grounded for reviewer use in the {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Improve retrieval quality or corpus relevance so key architect claims rely less on "
                        "fallback-only grounding."
                    ),
                )
        else:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_GROUNDING_BALANCE", status="fail", section="toc", detail=fallback_detail
                )
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_GROUNDING_FALLBACK_DOMINANT",
                    severity="high",
                    section="toc",
                    state=state,
                    message=(
                        "Architect claim grounding is fallback-dominant, so the ToC is not evidence-backed enough "
                        f"for serious review of the {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Ingest donor-relevant corpus and ensure the retriever returns traceable, high-confidence "
                        "evidence for key ToC claims."
                    ),
                )

    if len(architect_claim_citations) >= 3:
        traceability_complete = 0
        traceability_partial = 0
        traceability_missing = 0
        for citation in architect_claim_citations:
            status = citation_traceability_status(citation)
            if status == "complete":
                traceability_complete += 1
            elif status == "partial":
                traceability_partial += 1
            else:
                traceability_missing += 1
        traceability_gap = traceability_partial + traceability_missing
        traceability_gap_ratio = _safe_ratio(traceability_gap, len(architect_claim_citations))
        traceability_detail = (
            f"traceability_gap_rate={traceability_gap_ratio:.0%} "
            f"({traceability_gap}/{len(architect_claim_citations)})"
        )
        if traceability_gap_ratio < 0.3:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_TRACEABILITY_GAP", status="pass", section="toc", detail=traceability_detail
                )
            )
        elif traceability_gap_ratio < 0.6:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_TRACEABILITY_GAP", status="warn", section="toc", detail=traceability_detail
                )
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_TRACEABILITY_GAP_HIGH",
                    severity="medium",
                    section="toc",
                    state=state,
                    message=(
                        "Architect claim citations contain significant traceability gaps, so reviewers cannot reliably "
                        f"follow the { _donor_grounding_phrase(state) } evidence trail."
                    ),
                    fix_hint=(
                        "Ensure claim citations include traceable `doc_id`, `source`, `chunk`, and `page` metadata "
                        "for objective and result statements."
                    ),
                )
        else:
            checks.append(
                RuleCheckResult(
                    code="TOC_CLAIM_TRACEABILITY_GAP", status="fail", section="toc", detail=traceability_detail
                )
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_TRACEABILITY_GAP_CRITICAL",
                    severity="high",
                    section="toc",
                    state=state,
                    message=(
                        "Architect claim citations are mostly non-traceable, which blocks evidence review for the "
                        f"{_donor_review_package_phrase(state)}."
                    ),
                    fix_hint=(
                        "Regenerate the ToC with retrieval evidence that includes document, source, page, and chunk "
                        "references for reviewer traceability."
                    ),
                )

    threshold_evaluable = []
    threshold_hits = 0
    for citation in architect_claim_citations:
        threshold = citation.get("confidence_threshold")
        confidence = citation.get("citation_confidence")
        try:
            threshold_value = float(threshold) if threshold is not None else None
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            threshold_value = None
            confidence_value = None
        if threshold_value is None or confidence_value is None:
            continue
        threshold_evaluable.append((confidence_value, threshold_value))
        if confidence_value >= threshold_value:
            threshold_hits += 1
    if len(threshold_evaluable) >= 3:
        threshold_hit_rate = _safe_ratio(threshold_hits, len(threshold_evaluable))
        detail = f"threshold_hit_rate={threshold_hit_rate:.0%} ({threshold_hits}/{len(threshold_evaluable)})"
        if threshold_hit_rate >= 0.5:
            checks.append(
                RuleCheckResult(code="TOC_CLAIM_CONFIDENCE_HIT_RATE", status="pass", section="toc", detail=detail)
            )
        elif threshold_hit_rate >= 0.3:
            checks.append(
                RuleCheckResult(code="TOC_CLAIM_CONFIDENCE_HIT_RATE", status="warn", section="toc", detail=detail)
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_CONFIDENCE_HIT_RATE_LOW",
                    severity="medium",
                    section="toc",
                    state=state,
                    message=(
                        "Too few architect claim citations meet donor confidence thresholds for reliable review of the "
                        f"{_donor_review_package_phrase(state)}."
                    ),
                    fix_hint="Improve evidence matching and reduce weakly grounded objective and result claims before the next draft.",
                )
        else:
            checks.append(
                RuleCheckResult(code="TOC_CLAIM_CONFIDENCE_HIT_RATE", status="fail", section="toc", detail=detail)
            )
            if architect_rag_enabled:
                _add_flaw(
                    flaws,
                    code="TOC_CLAIM_CONFIDENCE_HIT_RATE_CRITICAL",
                    severity="high",
                    section="toc",
                    state=state,
                    message=(
                        "Architect claim citations rarely meet donor confidence thresholds, leaving the ToC too weakly "
                        f"grounded for approval review in the {_donor_review_package_phrase(state)}."
                    ),
                    fix_hint="Refine corpus and query strategy, then regenerate the ToC with stronger grounded evidence for key claims.",
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
        placeholder_rows = []
        for idx, indicator in enumerate(indicators):
            if not isinstance(indicator, dict):
                continue
            baseline = indicator.get("baseline")
            target = indicator.get("target")
            if _is_placeholder_baseline_target(baseline) or _is_placeholder_baseline_target(target):
                placeholder_rows.append(
                    {
                        "indicator_id": str(indicator.get("indicator_id") or f"IND_{idx + 1:03d}"),
                        "baseline": str(baseline or "").strip(),
                        "target": str(target or "").strip(),
                    }
                )

        if placeholder_rows:
            placeholder_ratio = _safe_ratio(len(placeholder_rows), len(indicators))
            detail = (
                f"{len(placeholder_rows)}/{len(indicators)} indicators with placeholder baseline/target "
                f"(ratio={placeholder_ratio:.0%})"
            )
            if placeholder_ratio > 0.5:
                checks.append(
                    RuleCheckResult(
                        code="LOGFRAME_BASELINE_TARGET_COMPLETENESS",
                        status="fail",
                        section="logframe",
                        detail=detail,
                    )
                )
                _add_flaw(
                    flaws,
                    code="LOGFRAME_BASELINE_TARGET_PLACEHOLDERS_CRITICAL",
                    severity="high",
                    section="logframe",
                    state=state,
                    message=(
                        "Most indicators still use placeholder baseline and target values, so the LogFrame is not yet "
                        f"reviewer-ready for {_donor_measurement_phrase(state)}."
                    ),
                    fix_hint=(
                        "Replace placeholder baseline and target values with concrete, measurable figures before the "
                        "next export or review cycle."
                    ),
                )
            else:
                checks.append(
                    RuleCheckResult(
                        code="LOGFRAME_BASELINE_TARGET_COMPLETENESS",
                        status="warn",
                        section="logframe",
                        detail=detail,
                    )
                )
                _add_flaw(
                    flaws,
                    code="LOGFRAME_BASELINE_TARGET_PLACEHOLDERS",
                    severity="medium",
                    section="logframe",
                    state=state,
                    message=(
                        "Some indicators still use placeholder baseline and target values, which keeps part of the "
                        f"LogFrame weak for {_donor_measurement_phrase(state)}."
                    ),
                    fix_hint=(
                        "Fill baseline and target fields with concrete measurable values for every affected indicator "
                        "before the next review pass."
                    ),
                )
        else:
            checks.append(
                RuleCheckResult(
                    code="LOGFRAME_BASELINE_TARGET_COMPLETENESS",
                    status="pass",
                    section="logframe",
                    detail="All indicators have non-placeholder baseline/target values",
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
            message=f"LogFrame/MEL indicators are missing, so the {_donor_review_package_phrase(state)} cannot yet be reviewed end to end.",
            fix_hint=(
                "Run MEL specialist and ensure indicator extraction or fallback indicator generation succeeds so the "
                f"draft can be reviewed against the {_donor_schema_phrase(state)}."
            ),
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
            message=(
                "Indicators are not accompanied by citation traceability, so reviewers cannot verify the monitoring "
                f"logic behind the {_donor_review_package_phrase(state)}."
            ),
            fix_hint=(
                "Ensure the MEL step records citation metadata for retrieved or fallback indicators, including enough "
                "detail for reviewer traceability."
            ),
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
