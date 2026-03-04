from __future__ import annotations

from typing import Any, Dict, Iterable


def unwrap_toc_payload(toc_payload: Any) -> Dict[str, Any]:
    if not isinstance(toc_payload, dict):
        return {}
    toc_root = toc_payload.get("toc")
    if isinstance(toc_root, dict):
        return toc_root
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


def normalize_toc_for_export(donor_key: str, toc_payload: Dict[str, Any]) -> Dict[str, Any]:
    toc = unwrap_toc_payload(toc_payload)
    key = str(donor_key or "").strip().lower()
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
