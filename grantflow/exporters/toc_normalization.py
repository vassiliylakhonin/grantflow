from __future__ import annotations

from typing import Any, Dict, Iterable


def unwrap_toc_payload(toc_payload: Any) -> Dict[str, Any]:
    if not isinstance(toc_payload, dict):
        return {}
    toc_root = toc_payload.get("toc")
    if isinstance(toc_root, dict):
        root = dict(toc_root)
        proposal_mode = toc_payload.get("proposal_mode")
        if proposal_mode and "proposal_mode" not in root:
            root["proposal_mode"] = proposal_mode
        rfq_profile = toc_payload.get("rfq_profile")
        if rfq_profile and "rfq_profile" not in root:
            root["rfq_profile"] = rfq_profile
        return root
    return toc_payload


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _pick_first_text(payload: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = _clean_text(payload.get(key))
        if value:
            return value
    return ""


def _pick_first_list(payload: Dict[str, Any], keys: Iterable[str]) -> list[Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list) and value:
            return value
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _to_str_list(value: Any) -> list[str]:
    items = []
    for item in _coerce_list(value):
        text = _clean_text(item)
        if text:
            items.append(text)
    return items


def _normalize_usaid_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    project_goal = _pick_first_text(
        toc,
        (
            "project_goal",
            "goal",
            "program_goal",
            "programme_objective",
            "project_development_objective",
            "pdo",
        ),
    )
    development_objectives_raw = _pick_first_list(toc, ("development_objectives", "objectives", "specific_objectives"))

    development_objectives: list[dict[str, Any]] = []
    for idx, raw_do in enumerate(development_objectives_raw, start=1):
        row = raw_do if isinstance(raw_do, dict) else {"description": _clean_text(raw_do)}
        do_id = _pick_first_text(row, ("do_id", "objective_id", "id", "code")) or f"DO{idx}"
        do_description = _pick_first_text(row, ("description", "title", "objective", "name"))
        ir_rows = _pick_first_list(row, ("intermediate_results", "results", "irs"))
        intermediate_results: list[dict[str, Any]] = []

        for ir_idx, raw_ir in enumerate(ir_rows, start=1):
            ir_row = raw_ir if isinstance(raw_ir, dict) else {"description": _clean_text(raw_ir)}
            ir_id = (
                _pick_first_text(ir_row, ("ir_id", "result_id", "objective_id", "id", "code")) or f"{do_id}.IR{ir_idx}"
            )
            ir_description = _pick_first_text(ir_row, ("description", "title", "objective", "name"))
            output_rows = _pick_first_list(ir_row, ("outputs", "deliverables", "activities"))
            outputs: list[dict[str, Any]] = []

            for out_idx, raw_out in enumerate(output_rows, start=1):
                out_row = raw_out if isinstance(raw_out, dict) else {"description": _clean_text(raw_out)}
                output_id = _pick_first_text(out_row, ("output_id", "id", "code")) or f"{ir_id}.OUT{out_idx}"
                output_description = _pick_first_text(out_row, ("description", "title", "name"))
                indicator_rows = _pick_first_list(out_row, ("indicators", "indicator_list", "metrics"))
                indicators: list[dict[str, Any]] = []
                for ind_idx, raw_ind in enumerate(indicator_rows, start=1):
                    ind_row = raw_ind if isinstance(raw_ind, dict) else {"name": _clean_text(raw_ind)}
                    indicator_code = _pick_first_text(ind_row, ("indicator_code", "code", "indicator_id", "id"))
                    indicator_name = _pick_first_text(ind_row, ("name", "title", "indicator"))
                    target = _pick_first_text(ind_row, ("target", "value"))
                    justification = _pick_first_text(ind_row, ("justification", "rationale", "description"))
                    citation = _pick_first_text(ind_row, ("citation", "source", "reference"))
                    if indicator_code or indicator_name or target or justification or citation:
                        indicators.append(
                            {
                                "indicator_code": indicator_code or f"IND{ind_idx}",
                                "name": indicator_name,
                                "target": target,
                                "justification": justification,
                                "citation": citation,
                            }
                        )

                outputs.append(
                    {
                        "output_id": output_id,
                        "description": output_description,
                        "indicators": indicators,
                    }
                )

            intermediate_results.append(
                {
                    "ir_id": ir_id,
                    "description": ir_description,
                    "outputs": outputs,
                }
            )

        development_objectives.append(
            {
                "do_id": do_id,
                "description": do_description,
                "intermediate_results": intermediate_results,
            }
        )

    critical_assumptions = _to_str_list(toc.get("critical_assumptions"))
    if not critical_assumptions:
        critical_assumptions = _to_str_list(toc.get("assumptions"))

    return {
        "project_goal": project_goal,
        "development_objectives": development_objectives,
        "critical_assumptions": critical_assumptions,
    }


def _normalize_eu_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    overall = toc.get("overall_objective")
    if not isinstance(overall, dict):
        overall_text = _pick_first_text(toc, ("overall_objective", "overall_goal", "project_goal"))
        overall = {"objective_id": "", "title": overall_text, "rationale": ""}
    overall_objective = {
        "objective_id": _pick_first_text(overall, ("objective_id", "id", "code")),
        "title": _pick_first_text(overall, ("title", "objective", "name")) or _pick_first_text(toc, ("project_goal",)),
        "rationale": _pick_first_text(overall, ("rationale", "description", "justification")),
    }

    specific_rows = _pick_first_list(toc, ("specific_objectives", "objectives", "development_objectives"))
    specific_objectives = []
    for idx, raw in enumerate(specific_rows, start=1):
        row = raw if isinstance(raw, dict) else {"title": _clean_text(raw)}
        specific_objectives.append(
            {
                "objective_id": _pick_first_text(row, ("objective_id", "id", "code")) or f"SO{idx}",
                "title": _pick_first_text(row, ("title", "objective", "name")),
                "rationale": _pick_first_text(row, ("rationale", "description", "justification")),
            }
        )

    outcome_rows = _pick_first_list(toc, ("expected_outcomes", "outcomes", "results"))
    expected_outcomes = []
    for idx, raw in enumerate(outcome_rows, start=1):
        row = raw if isinstance(raw, dict) else {"title": _clean_text(raw)}
        expected_outcomes.append(
            {
                "outcome_id": _pick_first_text(row, ("outcome_id", "id", "code", "result_id")) or f"OUT{idx}",
                "title": _pick_first_text(row, ("title", "name", "outcome")),
                "expected_change": _pick_first_text(row, ("expected_change", "description", "rationale")),
            }
        )

    assumptions = _to_str_list(toc.get("assumptions"))
    risks = _to_str_list(toc.get("risks"))
    if not risks:
        risks = _to_str_list(toc.get("assumptions_risks"))

    return {
        "overall_objective": overall_objective,
        "specific_objectives": specific_objectives,
        "expected_outcomes": expected_outcomes,
        "assumptions": assumptions,
        "risks": risks,
    }


def _normalize_worldbank_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    project_development_objective = _pick_first_text(
        toc,
        ("project_development_objective", "pdo", "project_goal", "program_goal", "programme_objective"),
    )

    objective_rows = _pick_first_list(toc, ("objectives", "development_objectives", "specific_objectives"))
    objectives = []
    for idx, raw in enumerate(objective_rows, start=1):
        row = raw if isinstance(raw, dict) else {"title": _clean_text(raw)}
        objectives.append(
            {
                "objective_id": _pick_first_text(row, ("objective_id", "id", "code", "do_id")) or f"OBJ{idx}",
                "title": _pick_first_text(row, ("title", "objective", "name", "description")),
                "description": _pick_first_text(row, ("description", "rationale", "expected_change")),
            }
        )

    result_rows = _pick_first_list(toc, ("results_chain", "results", "outcomes", "expected_outcomes"))
    results_chain = []
    for idx, raw in enumerate(result_rows, start=1):
        row = raw if isinstance(raw, dict) else {"title": _clean_text(raw)}
        results_chain.append(
            {
                "result_id": _pick_first_text(row, ("result_id", "outcome_id", "id", "code")) or f"R{idx}",
                "title": _pick_first_text(row, ("title", "name", "result", "outcome")),
                "description": _pick_first_text(row, ("description", "expected_change", "rationale")),
                "indicator_focus": _pick_first_text(row, ("indicator_focus", "indicator", "focus")),
            }
        )

    assumptions = _to_str_list(toc.get("assumptions"))
    risks = _to_str_list(toc.get("risks"))
    if not risks:
        risks = _to_str_list(toc.get("assumptions_risks"))

    return {
        "project_development_objective": project_development_objective,
        "objectives": objectives,
        "results_chain": results_chain,
        "assumptions": assumptions,
        "risks": risks,
    }


def _normalize_giz_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    programme_objective = _pick_first_text(
        toc,
        ("programme_objective", "program_goal", "project_goal", "project_development_objective"),
    )
    outputs = _to_str_list(_pick_first_list(toc, ("outputs", "deliverables")))

    outcome_rows = _pick_first_list(toc, ("outcomes", "results", "expected_outcomes"))
    outcomes = []
    for raw in outcome_rows:
        row = raw if isinstance(raw, dict) else {"title": _clean_text(raw)}
        outcomes.append(
            {
                "title": _pick_first_text(row, ("title", "name", "objective")),
                "description": _pick_first_text(row, ("description", "expected_change")),
                "partner_role": _pick_first_text(row, ("partner_role", "owner", "implementer")),
            }
        )

    sustainability_factors = _to_str_list(toc.get("sustainability_factors"))
    assumptions_risks = _to_str_list(toc.get("assumptions_risks"))
    if not assumptions_risks:
        assumptions_risks = _to_str_list(toc.get("assumptions")) + _to_str_list(toc.get("risks"))

    return {
        "programme_objective": programme_objective,
        "outputs": outputs,
        "outcomes": outcomes,
        "sustainability_factors": sustainability_factors,
        "assumptions_risks": assumptions_risks,
    }


def _normalize_state_department_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    strategic_context = _pick_first_text(toc, ("strategic_context", "context", "background"))
    program_goal = _pick_first_text(toc, ("program_goal", "programme_goal", "project_goal"))

    objective_rows = _pick_first_list(toc, ("objectives", "specific_objectives", "development_objectives"))
    objectives = []
    for raw in objective_rows:
        row = raw if isinstance(raw, dict) else {"objective": _clean_text(raw)}
        objectives.append(
            {
                "objective": _pick_first_text(row, ("objective", "title", "name")),
                "line_of_effort": _pick_first_text(row, ("line_of_effort", "pillar", "theme")),
                "expected_change": _pick_first_text(row, ("expected_change", "description", "result")),
            }
        )

    stakeholder_map = _to_str_list(_pick_first_list(toc, ("stakeholder_map", "stakeholders")))
    risk_mitigation = _to_str_list(_pick_first_list(toc, ("risk_mitigation", "risks", "assumptions_risks")))

    return {
        "strategic_context": strategic_context,
        "program_goal": program_goal,
        "objectives": objectives,
        "stakeholder_map": stakeholder_map,
        "risk_mitigation": risk_mitigation,
    }


def _normalize_evaluation_rfq_toc(toc: Dict[str, Any]) -> Dict[str, Any]:
    method_rows = _pick_first_list(toc, ("methodology_components", "methods"))
    methodology_components = []
    for raw in method_rows:
        row = raw if isinstance(raw, dict) else {"method": _clean_text(raw)}
        methodology_components.append(
            {
                "method": _pick_first_text(row, ("method", "title", "name")),
                "purpose": _pick_first_text(row, ("purpose", "description", "expected_change")),
                "respondent_group": _pick_first_text(row, ("respondent_group", "stakeholders", "target_group")),
                "evidence_source": _pick_first_text(row, ("evidence_source", "source", "reference")),
            }
        )

    team_rows = _pick_first_list(toc, ("team_composition", "team_roles"))
    team_composition = []
    for raw in team_rows:
        row = raw if isinstance(raw, dict) else {"role": _clean_text(raw)}
        team_composition.append(
            {
                "role": _pick_first_text(row, ("role", "title", "name")),
                "responsibility": _pick_first_text(row, ("responsibility", "description", "purpose")),
            }
        )

    personnel_rows = _pick_first_list(toc, ("key_personnel", "personnel", "staffing_plan"))
    key_personnel = []
    for raw in personnel_rows:
        row = raw if isinstance(raw, dict) else {"name": _clean_text(raw)}
        key_personnel.append(
            {
                "name": _pick_first_text(row, ("name", "person", "staff_name")),
                "role": _pick_first_text(row, ("role", "title")),
                "qualifications": _pick_first_text(row, ("qualifications", "experience", "summary")),
                "level_of_effort": _pick_first_text(row, ("level_of_effort", "loe", "allocation")),
                "cv_status": _pick_first_text(row, ("cv_status", "status")),
            }
        )

    deliverable_rows = _pick_first_list(toc, ("deliverables",))
    deliverables = []
    for raw in deliverable_rows:
        row = raw if isinstance(raw, dict) else {"deliverable": _clean_text(raw)}
        deliverables.append(
            {
                "deliverable": _pick_first_text(row, ("deliverable", "title", "name")),
                "timing": _pick_first_text(row, ("timing", "window", "milestone")),
                "purpose": _pick_first_text(row, ("purpose", "description", "expected_change")),
            }
        )

    compliance_rows = _pick_first_list(toc, ("compliance_matrix", "compliance_requirements"))
    compliance_matrix = []
    for raw in compliance_rows:
        row = raw if isinstance(raw, dict) else {"requirement": _clean_text(raw)}
        compliance_matrix.append(
            {
                "requirement": _pick_first_text(row, ("requirement", "title", "name")),
                "response_section": _pick_first_text(row, ("response_section", "section")),
                "evidence": _pick_first_text(row, ("evidence", "attachment", "source")),
                "status": _pick_first_text(row, ("status",)),
                "notes": _pick_first_text(row, ("notes", "description")),
            }
        )

    cost_rows = _pick_first_list(toc, ("cost_structure", "financial_structure", "budget_structure"))
    cost_structure = []
    for raw in cost_rows:
        row = raw if isinstance(raw, dict) else {"cost_bucket": _clean_text(raw)}
        cost_structure.append(
            {
                "cost_bucket": _pick_first_text(row, ("cost_bucket", "bucket", "title", "name")),
                "basis": _pick_first_text(row, ("basis", "driver")),
                "estimate": _pick_first_text(row, ("estimate", "amount", "pricing_note")),
                "notes": _pick_first_text(row, ("notes", "description")),
            }
        )

    submission_rows = _pick_first_list(
        toc,
        ("submission_package_checklist", "submission_checklist", "attachment_manifest"),
    )
    submission_package_checklist = []
    for raw in submission_rows:
        row = raw if isinstance(raw, dict) else {"artifact": _clean_text(raw)}
        submission_package_checklist.append(
            {
                "artifact": _pick_first_text(row, ("artifact", "title", "name")),
                "owner": _pick_first_text(row, ("owner", "responsible_party")),
                "status": _pick_first_text(row, ("status",)),
                "notes": _pick_first_text(row, ("notes", "description")),
            }
        )

    attachment_rows = _pick_first_list(
        toc,
        ("attachment_manifest", "annex_manifest", "attachments"),
    )
    attachment_manifest = []
    for raw in attachment_rows:
        row = raw if isinstance(raw, dict) else {"attachment": _clean_text(raw)}
        attachment_manifest.append(
            {
                "attachment": _pick_first_text(row, ("attachment", "artifact", "title", "name")),
                "required_for": _pick_first_text(row, ("required_for", "response_section", "purpose")),
                "owner": _pick_first_text(row, ("owner", "responsible_party")),
                "status": _pick_first_text(row, ("status",)),
                "notes": _pick_first_text(row, ("notes", "description")),
            }
        )

    question_matrix_rows = _pick_first_list(toc, ("evaluation_questions_matrix", "question_matrix"))
    evaluation_questions_matrix = []
    for raw in question_matrix_rows:
        row = raw if isinstance(raw, dict) else {"evaluation_question": _clean_text(raw)}
        evaluation_questions_matrix.append(
            {
                "evaluation_question": _pick_first_text(row, ("evaluation_question", "question", "title", "name")),
                "key_methods": _to_str_list(_pick_first_list(row, ("key_methods", "methods"))),
                "evidence_sources": _to_str_list(_pick_first_list(row, ("evidence_sources", "sources", "evidence"))),
                "reporting_use": _pick_first_text(row, ("reporting_use", "purpose", "description")),
            }
        )

    method_coverage_rows = _pick_first_list(toc, ("methods_coverage_matrix", "method_coverage"))
    methods_coverage_matrix = []
    for raw in method_coverage_rows:
        row = raw if isinstance(raw, dict) else {"method": _clean_text(raw)}
        methods_coverage_matrix.append(
            {
                "method": _pick_first_text(row, ("method", "title", "name")),
                "covers_questions": _to_str_list(_pick_first_list(row, ("covers_questions", "questions"))),
                "respondent_group": _pick_first_text(row, ("respondent_group", "target_group", "stakeholders")),
                "expected_output": _pick_first_text(row, ("expected_output", "purpose", "description")),
            }
        )

    deliverable_schedule_rows = _pick_first_list(toc, ("deliverables_schedule_table", "deliverables_schedule"))
    deliverables_schedule_table = []
    for raw in deliverable_schedule_rows:
        row = raw if isinstance(raw, dict) else {"deliverable": _clean_text(raw)}
        deliverables_schedule_table.append(
            {
                "deliverable": _pick_first_text(row, ("deliverable", "title", "name")),
                "due_window": _pick_first_text(row, ("due_window", "timing", "window", "milestone")),
                "owner": _pick_first_text(row, ("owner", "responsible_party")),
                "dependencies": _to_str_list(_pick_first_list(row, ("dependencies", "inputs"))),
                "review_gate": _pick_first_text(row, ("review_gate", "approval_gate", "gate")),
            }
        )

    return {
        "proposal_mode": "evaluation_rfq",
        "rfq_profile": _pick_first_text(toc, ("rfq_profile", "profile")),
        "brief": _pick_first_text(toc, ("brief", "project_goal")),
        "background_context": _pick_first_text(toc, ("background_context", "background", "context")),
        "organization_information": _pick_first_text(toc, ("organization_information",)),
        "evaluation_purpose": _pick_first_text(toc, ("evaluation_purpose", "purpose")),
        "evaluation_questions": _to_str_list(_pick_first_list(toc, ("evaluation_questions", "key_questions"))),
        "technical_approach_summary": _pick_first_text(toc, ("technical_approach_summary", "technical_approach")),
        "methodology_overview": _pick_first_text(toc, ("methodology_overview", "methodology", "approach")),
        "methodology_components": methodology_components,
        "sampling_plan": _pick_first_text(toc, ("sampling_plan",)),
        "analytical_software": _to_str_list(_pick_first_list(toc, ("analytical_software", "analysis_software"))),
        "ethical_considerations": _to_str_list(_pick_first_list(toc, ("ethical_considerations", "ethics"))),
        "team_composition": team_composition,
        "key_personnel": key_personnel,
        "level_of_effort_summary": _pick_first_text(toc, ("level_of_effort_summary", "loe_summary")),
        "technical_experience_summary": _pick_first_text(
            toc, ("technical_experience_summary", "past_performance_summary")
        ),
        "sample_outputs_summary": _pick_first_text(toc, ("sample_outputs_summary", "sample_output_summary")),
        "financial_summary": _pick_first_text(toc, ("financial_summary", "budget_summary")),
        "cost_structure": cost_structure,
        "pricing_assumptions": _to_str_list(_pick_first_list(toc, ("pricing_assumptions", "financial_assumptions"))),
        "payment_schedule_summary": _pick_first_text(toc, ("payment_schedule_summary", "payment_schedule")),
        "submission_package_checklist": submission_package_checklist,
        "attachment_manifest": attachment_manifest,
        "evaluation_questions_matrix": evaluation_questions_matrix,
        "methods_coverage_matrix": methods_coverage_matrix,
        "deliverables_schedule_table": deliverables_schedule_table,
        "deliverables": deliverables,
        "workplan_summary": _to_str_list(_pick_first_list(toc, ("workplan_summary", "workplan"))),
        "assumptions_risks": _to_str_list(_pick_first_list(toc, ("assumptions_risks", "risks", "assumptions"))),
        "annex_readiness": _to_str_list(_pick_first_list(toc, ("annex_readiness", "annexes"))),
        "compliance_matrix": compliance_matrix,
    }


def normalize_toc_for_export(donor_key: str, toc_payload: Dict[str, Any]) -> Dict[str, Any]:
    toc = unwrap_toc_payload(toc_payload)
    key = str(donor_key or "").strip().lower()
    if key == "evaluation_rfq":
        return _normalize_evaluation_rfq_toc(toc)
    if key == "usaid":
        return _normalize_usaid_toc(toc)
    if key == "eu":
        return _normalize_eu_toc(toc)
    if key == "worldbank":
        return _normalize_worldbank_toc(toc)
    if key == "giz":
        return _normalize_giz_toc(toc)
    if key == "state_department":
        return _normalize_state_department_toc(toc)
    return toc
