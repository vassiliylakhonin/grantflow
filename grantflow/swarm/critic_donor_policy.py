from __future__ import annotations

from typing import Any, Callable

from grantflow.swarm.state_contract import state_donor_id


def normalized_donor_id(state: dict[str, Any]) -> str:
    return state_donor_id(state)


def apply_donor_specific_toc_checks(
    *,
    state: dict[str, Any],
    toc_payload: Any,
    check_fn: Callable[..., None],
    add_flaw_fn: Callable[..., None],
) -> None:
    donor = normalized_donor_id(state)
    if not isinstance(toc_payload, dict):
        return

    if donor == "usaid":
        dos = toc_payload.get("development_objectives")
        if isinstance(dos, list) and dos:
            check_fn(code="USAID_DO_PRESENT", status="pass", section="toc", detail=f"{len(dos)} DO(s)")
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
                check_fn(code="USAID_IR_HIERARCHY", status="fail", section="toc", detail="One or more DOs missing IRs")
                add_flaw_fn(
                    code="USAID_IR_MISSING",
                    severity="high",
                    section="toc",
                    message="USAID results hierarchy is not review-ready: one or more Development Objectives do not yet break down into Intermediate Results.",
                    fix_hint="Add `development_objectives[].intermediate_results[]` so each DO has a complete DO -> IR cascade that proposal reviewers can map into the USAID results framework and PMP logic.",
                )
            else:
                check_fn(code="USAID_IR_HIERARCHY", status="pass", section="toc", detail=f"{ir_count} IR(s)")

            if missing_outputs:
                check_fn(
                    code="USAID_OUTPUT_HIERARCHY",
                    status="fail",
                    section="toc",
                    detail="One or more IRs missing outputs",
                )
                add_flaw_fn(
                    code="USAID_OUTPUTS_MISSING",
                    severity="high",
                    section="toc",
                    message="USAID results hierarchy is not review-ready: one or more Intermediate Results do not yet resolve into outputs or deliverables.",
                    fix_hint="Populate `intermediate_results[].outputs[]` under each USAID IR so reviewers can trace implementation deliverables, monitoring rows, and evidence expectations before approval.",
                )
            else:
                check_fn(
                    code="USAID_OUTPUT_HIERARCHY", status="pass", section="toc", detail=f"{output_count} output(s)"
                )
        else:
            check_fn(code="USAID_DO_PRESENT", status="fail", section="toc", detail="No development_objectives")
            add_flaw_fn(
                code="USAID_DO_MISSING",
                severity="high",
                section="toc",
                message="USAID ToC is missing Development Objectives, so the results hierarchy cannot yet be reviewed as a donor package.",
                fix_hint="Add at least one `development_objective` with a DO -> IR -> Output cascade aligned to the intended USAID monitoring package and reviewer expectations.",
            )

        assumptions = toc_payload.get("critical_assumptions")
        if isinstance(assumptions, list) and assumptions:
            check_fn(
                code="USAID_CRITICAL_ASSUMPTIONS_PRESENT",
                status="pass",
                section="toc",
                detail=f"{len(assumptions)} assumptions",
            )
        else:
            check_fn(
                code="USAID_CRITICAL_ASSUMPTIONS_PRESENT",
                status="warn",
                section="toc",
                detail="No critical_assumptions",
            )
            add_flaw_fn(
                code="USAID_ASSUMPTIONS_MISSING",
                severity="medium",
                section="toc",
                message="USAID ToC is missing critical assumptions, leaving the results logic weak for review and adaptive management.",
                fix_hint="Add `critical_assumptions` describing the external conditions that must hold for the DO -> IR -> Output logic to remain credible during review, CLA discussion, and monitoring.",
            )
        return

    if donor == "eu":
        overall = toc_payload.get("overall_objective")
        if isinstance(overall, dict):
            missing = [k for k in ("objective_id", "title", "rationale") if not str(overall.get(k) or "").strip()]
            if not missing:
                check_fn(code="EU_OVERALL_OBJECTIVE_COMPLETE", status="pass", section="toc")
            else:
                check_fn(
                    code="EU_OVERALL_OBJECTIVE_COMPLETE",
                    status="fail",
                    section="toc",
                    detail=f"Missing fields: {', '.join(missing)}",
                )
                add_flaw_fn(
                    code="EU_INTERVENTION_LOGIC_INCOMPLETE",
                    severity="high",
                    section="toc",
                    message="EU intervention logic is not review-ready: the overall objective is missing the core fields needed to anchor the action logic.",
                    fix_hint="Populate `overall_objective.objective_id`, `title`, and `rationale` so the overall objective can anchor the EU intervention logic, verification narrative, and results chain review.",
                )
        else:
            check_fn(
                code="EU_OVERALL_OBJECTIVE_COMPLETE", status="fail", section="toc", detail="Missing overall_objective"
            )
            add_flaw_fn(
                code="EU_OVERALL_OBJECTIVE_MISSING",
                severity="high",
                section="toc",
                message="EU ToC is missing the overall objective, so the intervention logic does not yet have a credible top-line anchor for review.",
                fix_hint="Provide an EU intervention-logic style `overall_objective` with rationale so reviewers can distinguish the overall objective, specific objectives, expected outcomes, and verification logic.",
            )

        specific_objectives = toc_payload.get("specific_objectives")
        if isinstance(specific_objectives, list) and specific_objectives:
            incomplete = False
            for row in specific_objectives:
                if not isinstance(row, dict):
                    incomplete = True
                    break
                if not all(str(row.get(k) or "").strip() for k in ("objective_id", "title", "rationale")):
                    incomplete = True
                    break
            if incomplete:
                check_fn(
                    code="EU_SPECIFIC_OBJECTIVES_COMPLETE",
                    status="warn",
                    section="toc",
                    detail="One or more specific objectives are incomplete",
                )
                add_flaw_fn(
                    code="EU_SPECIFIC_OBJECTIVES_INCOMPLETE",
                    severity="medium",
                    section="toc",
                    message="EU specific objectives are not yet detailed enough for intervention-logic review.",
                    fix_hint="Complete `objective_id`, `title`, and `rationale` for each `specific_objectives[]` entry so objective-level monitoring, means of verification, and delivery accountability can be traced cleanly.",
                )
            else:
                check_fn(
                    code="EU_SPECIFIC_OBJECTIVES_COMPLETE",
                    status="pass",
                    section="toc",
                    detail=f"{len(specific_objectives)} specific objective(s)",
                )
        else:
            check_fn(
                code="EU_SPECIFIC_OBJECTIVES_COMPLETE",
                status="warn",
                section="toc",
                detail="No specific_objectives",
            )
            add_flaw_fn(
                code="EU_SPECIFIC_OBJECTIVES_MISSING",
                severity="medium",
                section="toc",
                message="EU ToC is missing specific objectives required for intervention-logic review.",
                fix_hint="Populate `specific_objectives[]` aligned with the intervention logic so outputs and expected outcomes can be linked to objective-level review.",
            )

        outcomes = toc_payload.get("expected_outcomes")
        if isinstance(outcomes, list) and outcomes:
            check_fn(
                code="EU_EXPECTED_OUTCOMES_PRESENT",
                status="pass",
                section="toc",
                detail=f"{len(outcomes)} expected outcome(s)",
            )
        else:
            check_fn(
                code="EU_EXPECTED_OUTCOMES_PRESENT",
                status="warn",
                section="toc",
                detail="No expected_outcomes",
            )
            add_flaw_fn(
                code="EU_EXPECTED_OUTCOMES_MISSING",
                severity="medium",
                section="toc",
                message="EU ToC is missing expected outcomes, so the intervention logic cannot yet show measurable downstream change.",
                fix_hint="Add `expected_outcomes[]` entries with measurable expected change so the EU package shows a clear path from specific objectives to outcome evidence and verification.",
            )
        return

    if donor == "giz":
        outcomes = toc_payload.get("outcomes")
        if isinstance(outcomes, list) and outcomes:
            check_fn(code="GIZ_OUTCOMES_PRESENT", status="pass", section="toc", detail=f"{len(outcomes)} outcomes")
            missing_partner_role = False
            for row in outcomes:
                if not isinstance(row, dict) or not str(row.get("partner_role") or "").strip():
                    missing_partner_role = True
                    break
            if missing_partner_role:
                check_fn(
                    code="GIZ_PARTNER_ROLE_PRESENT",
                    status="fail",
                    section="toc",
                    detail="One or more outcomes missing partner_role",
                )
                add_flaw_fn(
                    code="GIZ_PARTNER_ROLE_MISSING",
                    severity="medium",
                    section="toc",
                    message="GIZ outcomes should identify partner roles.",
                    fix_hint="Populate `outcomes[].partner_role` for technical cooperation implementation responsibility.",
                )
            else:
                check_fn(code="GIZ_PARTNER_ROLE_PRESENT", status="pass", section="toc")
        else:
            check_fn(code="GIZ_OUTCOMES_PRESENT", status="fail", section="toc", detail="No outcomes")
            add_flaw_fn(
                code="GIZ_OUTCOMES_MISSING",
                severity="high",
                section="toc",
                message="GIZ ToC is missing outcomes.",
                fix_hint="Add practical outcomes aligned with technical cooperation objectives and partners.",
            )

        sustainability = toc_payload.get("sustainability_factors")
        if isinstance(sustainability, list) and sustainability:
            check_fn(
                code="GIZ_SUSTAINABILITY_FACTORS_PRESENT",
                status="pass",
                section="toc",
                detail=f"{len(sustainability)} factors",
            )
        else:
            check_fn(
                code="GIZ_SUSTAINABILITY_FACTORS_PRESENT",
                status="warn",
                section="toc",
                detail="No sustainability_factors",
            )
            add_flaw_fn(
                code="GIZ_SUSTAINABILITY_FACTORS_MISSING",
                severity="medium",
                section="toc",
                message="GIZ ToC should include sustainability factors.",
                fix_hint="Add `sustainability_factors` covering institutionalization and continuation after project support.",
            )
        return

    if donor in {"state_department", "us_state_department", "us_state_department_guidance"}:
        for key, code, msg, hint in [
            (
                "strategic_context",
                "STATE_STRATEGIC_CONTEXT_PRESENT",
                "State Department ToC should include strategic context.",
                "Populate `strategic_context` with country/political/program context.",
            ),
        ]:
            if str(toc_payload.get(key) or "").strip():
                check_fn(code=code, status="pass", section="toc")
            else:
                check_fn(code=code, status="fail", section="toc", detail=f"Missing {key}")
                add_flaw_fn(
                    code=f"{code}_MISSING",
                    severity="high",
                    section="toc",
                    message=msg,
                    fix_hint=f"{hint} This should be explicit enough for State Department reviewer triage, partner-risk review, and bureau/program decision-making.",
                )
        for key, code, label in [
            ("stakeholder_map", "STATE_STAKEHOLDER_MAP_PRESENT", "stakeholder_map"),
            ("risk_mitigation", "STATE_RISK_MITIGATION_PRESENT", "risk_mitigation"),
        ]:
            rows = toc_payload.get(key)
            if isinstance(rows, list) and rows:
                check_fn(code=code, status="pass", section="toc", detail=f"{len(rows)} {label} entries")
            else:
                check_fn(code=code, status="warn", section="toc", detail=f"No {label}")
                add_flaw_fn(
                    code=f"{code}_MISSING",
                    severity="medium",
                    section="toc",
                    message=f"State Department ToC is missing {label.replace('_', ' ')}, leaving reviewer governance and partner-risk assessment under-specified.",
                    fix_hint=f"Add `{key}` entries so stakeholder logic, mitigation choices, and partner-risk planning are explicit in the State Department review package.",
                )
        return

    if donor == "worldbank":
        pdo = str(toc_payload.get("project_development_objective") or "").strip()
        if pdo:
            check_fn(code="WB_PDO_PRESENT", status="pass", section="toc")
        else:
            check_fn(
                code="WB_PDO_PRESENT", status="warn", section="toc", detail="Missing project_development_objective"
            )
            add_flaw_fn(
                code="WB_PDO_MISSING",
                severity="medium",
                section="toc",
                message="World Bank ToC is missing the PDO, so the results framework has no clear anchor for reviewer alignment.",
                fix_hint="Populate `project_development_objective` with a concise PDO statement so reviewers can align objectives, results-chain rows, and indicator focus to the World Bank framework.",
            )

        objectives = toc_payload.get("objectives")
        if isinstance(objectives, list) and objectives:
            check_fn(code="WB_OBJECTIVES_PRESENT", status="pass", section="toc", detail=f"{len(objectives)} objectives")
            incomplete = False
            for obj in objectives:
                if not isinstance(obj, dict):
                    incomplete = True
                    break
                if not all(str(obj.get(k) or "").strip() for k in ("objective_id", "title", "description")):
                    incomplete = True
                    break
            if incomplete:
                check_fn(
                    code="WB_OBJECTIVES_COMPLETE", status="fail", section="toc", detail="Incomplete objective fields"
                )
                add_flaw_fn(
                    code="WB_OBJECTIVE_FIELDS_INCOMPLETE",
                    severity="high",
                    section="toc",
                    message="World Bank objectives are not review-ready: required fields are missing for results-framework alignment.",
                    fix_hint="Complete `objective_id`, `title`, and `description` for each `objectives[]` entry so the PDO, implementation logic, and downstream results-chain rows can be reviewed cleanly.",
                )
            else:
                check_fn(code="WB_OBJECTIVES_COMPLETE", status="pass", section="toc")
        else:
            check_fn(code="WB_OBJECTIVES_PRESENT", status="fail", section="toc", detail="No objectives")
            add_flaw_fn(
                code="WB_OBJECTIVES_MISSING",
                severity="high",
                section="toc",
                message="World Bank ToC is missing objectives, so the results framework cannot yet be decomposed into reviewable lines.",
                fix_hint="Add at least one objective with ID, title, and description so the PDO can be decomposed into reviewable objective and indicator lines for results-framework review.",
            )

        results_chain = toc_payload.get("results_chain")
        if isinstance(results_chain, list) and results_chain:
            check_fn(
                code="WB_RESULTS_CHAIN_PRESENT", status="pass", section="toc", detail=f"{len(results_chain)} results"
            )
            incomplete_result = False
            for row in results_chain:
                if not isinstance(row, dict):
                    incomplete_result = True
                    break
                if not all(
                    str(row.get(k) or "").strip() for k in ("result_id", "title", "description", "indicator_focus")
                ):
                    incomplete_result = True
                    break
            if incomplete_result:
                check_fn(
                    code="WB_RESULTS_CHAIN_COMPLETE",
                    status="warn",
                    section="toc",
                    detail="One or more results_chain entries are incomplete",
                )
                add_flaw_fn(
                    code="WB_RESULTS_CHAIN_INCOMPLETE",
                    severity="medium",
                    section="toc",
                    message="World Bank results-chain entries are not yet detailed enough for framework review.",
                    fix_hint="Complete `result_id`, `title`, `description`, and `indicator_focus` for each `results_chain[]` entry so the results framework reads like a reviewer-ready chain with clear monitoring focus.",
                )
            else:
                check_fn(code="WB_RESULTS_CHAIN_COMPLETE", status="pass", section="toc")
        else:
            check_fn(code="WB_RESULTS_CHAIN_PRESENT", status="warn", section="toc", detail="No results_chain")
            add_flaw_fn(
                code="WB_RESULTS_CHAIN_MISSING",
                severity="medium",
                section="toc",
                message="World Bank ToC is missing the results chain, so reviewers cannot trace the PDO into concrete monitored results.",
                fix_hint="Add `results_chain[]` entries linked to objectives and indicator focus so reviewers can trace the PDO into concrete results rows, verification logic, and ISR-style monitoring.",
            )
        return
