from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from grantflow.exporters.template_profile import (
    TEMPLATE_DISPLAY_NAMES,
    build_export_template_profile,
    resolve_export_template_key,
)
from grantflow.exporters.toc_normalization import normalize_toc_for_export, unwrap_toc_payload

DONOR_DOCX_EXPECTED_HEADINGS: dict[str, list[str]] = {
    "evaluation_rfq": [
        "Evaluation RFQ Technical Proposal",
        "Organization Information",
        "Assignment Background",
        "Evaluation Purpose",
        "Methodology",
        "Analysis and Proposed Approaches / Methodologies",
        "Personnel and Team Composition",
        "Proposed Level of Effort",
        "Technical Experience and Past Performance References",
        "Workplan & Deliverables",
    ],
    "usaid": ["USAID Results Framework", "Project Goal", "Development Objectives", "Critical Assumptions"],
    "eu": ["EU Intervention Logic", "Overall Objective", "Specific Objectives", "Expected Outcomes"],
    "worldbank": [
        "World Bank Results Framework",
        "Project Development Objective (PDO)",
        "Objectives",
        "Results Chain",
    ],
    "giz": ["GIZ Results & Sustainability Logic", "Programme Objective", "Outcomes", "Sustainability Factors"],
    "un_agencies": ["UN Agency Program Logic", "Overview", "Development Objectives"],
    "state_department": ["U.S. Department of State Program Logic", "Program Goal", "Objectives", "Risk Mitigation"],
}

DONOR_XLSX_REQUIRED_SHEETS: dict[str, list[str]] = {
    "evaluation_rfq": ["LogFrame", "Evaluation_Plan", "Template Meta"],
    "usaid": ["LogFrame", "USAID_RF", "Template Meta"],
    "eu": ["LogFrame", "EU_Intervention", "EU_Assumptions_Risks", "Template Meta"],
    "worldbank": ["LogFrame", "WB_Results", "Template Meta"],
    "giz": ["LogFrame", "GIZ_Results", "Template Meta"],
    "un_agencies": ["LogFrame", "UN_Results", "Template Meta"],
    "state_department": ["LogFrame", "StateDept_Results", "Template Meta"],
}

DONOR_XLSX_PRIMARY_SHEET: dict[str, str] = {
    "evaluation_rfq": "Evaluation_Plan",
    "usaid": "USAID_RF",
    "eu": "EU_Intervention",
    "worldbank": "WB_Results",
    "giz": "GIZ_Results",
    "un_agencies": "UN_Results",
    "state_department": "StateDept_Results",
}

DONOR_XLSX_PRIMARY_HEADERS: dict[str, list[str]] = {
    "evaluation_rfq": ["Section", "ID", "Title", "Description"],
    "usaid": ["DO ID", "DO Description", "IR ID", "IR Description"],
    "eu": ["Level", "ID", "Title", "Description"],
    "worldbank": ["Level", "ID", "Title", "Description"],
    "giz": ["Level", "Title", "Description", "Partner Role"],
    "un_agencies": ["Level", "Title", "Description", "Suggested Monitoring Focus"],
    "state_department": ["Level", "Objective / Title", "Line of Effort", "Description"],
}
EXPORT_CONTRACT_POLICY_MODES = {"off", "warn", "strict"}


def _status_bucket_counts(rows: Any, *, label_key: str) -> Dict[str, Any]:
    if not isinstance(rows, list):
        return {"total": 0, "ready": 0, "partial": 0, "pending": 0, "labeled": 0}

    ready = partial = pending = labeled = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get(label_key) or "").strip():
            labeled += 1
        status = str(row.get("status") or "").strip().lower()
        if status == "ready":
            ready += 1
        elif status == "partial":
            partial += 1
        elif status:
            pending += 1
    return {
        "total": len([row for row in rows if isinstance(row, dict)]),
        "ready": ready,
        "partial": partial,
        "pending": pending,
        "labeled": labeled,
    }


def _evaluation_rfq_submission_summary(normalized_toc: Dict[str, Any]) -> Dict[str, Any]:
    submission_counts = _status_bucket_counts(
        normalized_toc.get("submission_package_checklist"),
        label_key="artifact",
    )
    attachment_counts = _status_bucket_counts(
        normalized_toc.get("attachment_manifest"),
        label_key="attachment",
    )
    compliance_counts = _status_bucket_counts(
        normalized_toc.get("compliance_matrix"),
        label_key="requirement",
    )

    weighted_total = submission_counts["total"] + attachment_counts["total"] + compliance_counts["total"]
    weighted_ready = submission_counts["ready"] + attachment_counts["ready"] + compliance_counts["ready"]
    weighted_partial = submission_counts["partial"] + attachment_counts["partial"] + compliance_counts["partial"]
    completeness_score = (
        round(((weighted_ready + (0.5 * weighted_partial)) / weighted_total) * 100, 1) if weighted_total else 0.0
    )
    if weighted_total == 0:
        readiness_status = "missing"
    elif completeness_score >= 85:
        readiness_status = "ready"
    elif completeness_score >= 60:
        readiness_status = "partial"
    else:
        readiness_status = "weak"

    top_gap = "none"
    gaps = {
        "submission_package": submission_counts["pending"]
        + max(0, submission_counts["total"] - submission_counts["labeled"]),
        "attachment_manifest": attachment_counts["pending"]
        + max(0, attachment_counts["total"] - attachment_counts["labeled"]),
        "compliance_matrix": compliance_counts["pending"]
        + max(0, compliance_counts["total"] - compliance_counts["labeled"]),
    }
    if any(value > 0 for value in gaps.values()):
        top_gap = max(gaps, key=lambda gap_key: gaps[gap_key])

    return {
        "completeness_score": completeness_score,
        "readiness_status": readiness_status,
        "top_gap": top_gap,
        "submission_package_counts": submission_counts,
        "attachment_manifest_counts": attachment_counts,
        "compliance_matrix_counts": compliance_counts,
    }


def normalize_export_contract_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in EXPORT_CONTRACT_POLICY_MODES:
        return "warn"
    return mode


def normalize_toc_payload(toc_payload: Dict[str, Any]) -> Dict[str, Any]:
    return unwrap_toc_payload(toc_payload)


def evaluate_export_contract(
    *,
    donor_id: str,
    toc_payload: Dict[str, Any],
    workbook_sheetnames: Optional[Iterable[str]] = None,
    workbook_primary_sheet_headers: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    donor_key = resolve_export_template_key(donor_id=donor_id, toc_payload=toc_payload)
    toc_root = normalize_toc_payload(toc_payload if isinstance(toc_payload, dict) else {})
    normalized_toc = normalize_toc_for_export(donor_key, toc_root)
    profile = build_export_template_profile(donor_id=donor_id, toc_payload=normalized_toc)

    required_sections = list(profile.get("required_sections") or [])
    missing_required_sections = list(profile.get("missing_sections") or [])
    present_required_sections = list(profile.get("present_sections") or [])

    required_sheets = list(DONOR_XLSX_REQUIRED_SHEETS.get(donor_key, []))
    workbook_validation_enabled = workbook_sheetnames is not None or workbook_primary_sheet_headers is not None
    actual_sheets = [str(x) for x in (workbook_sheetnames or [])] if workbook_validation_enabled else []
    missing_required_sheets = (
        [name for name in required_sheets if name not in actual_sheets] if workbook_validation_enabled else []
    )

    expected_docx_headings = list(DONOR_DOCX_EXPECTED_HEADINGS.get(donor_key, []))
    primary_sheet = DONOR_XLSX_PRIMARY_SHEET.get(donor_key)
    primary_headers = list(DONOR_XLSX_PRIMARY_HEADERS.get(donor_key, []))
    actual_primary_headers = (
        [str(x) for x in (workbook_primary_sheet_headers or [])] if workbook_validation_enabled else []
    )
    missing_primary_sheet_headers = (
        [name for name in primary_headers if name not in actual_primary_headers]
        if workbook_validation_enabled and primary_headers
        else []
    )

    status = (
        "pass"
        if not missing_required_sections and not missing_required_sheets and not missing_primary_sheet_headers
        else "warning"
    )
    warnings: list[str] = []
    if missing_required_sections:
        warnings.append("missing_required_toc_sections")
    if workbook_validation_enabled and missing_required_sheets:
        warnings.append("missing_required_workbook_sheets")
    if workbook_validation_enabled and missing_primary_sheet_headers:
        warnings.append("missing_required_primary_sheet_headers")

    submission_readiness_summary: Dict[str, Any] | None = None
    if donor_key == "evaluation_rfq":
        submission_readiness_summary = _evaluation_rfq_submission_summary(normalized_toc)
        if submission_readiness_summary.get("readiness_status") in {"missing", "weak"}:
            warnings.append("submission_completeness_low")

    return {
        "donor_id": str(donor_id or ""),
        "template_key": donor_key,
        "template_display_name": TEMPLATE_DISPLAY_NAMES.get(donor_key, TEMPLATE_DISPLAY_NAMES["generic"]),
        "required_sections": required_sections,
        "present_sections": present_required_sections,
        "missing_required_sections": missing_required_sections,
        "required_sheets": required_sheets,
        "actual_sheets": actual_sheets,
        "missing_required_sheets": missing_required_sheets,
        "expected_docx_headings": expected_docx_headings,
        "expected_primary_sheet": primary_sheet,
        "expected_primary_sheet_headers": primary_headers,
        "actual_primary_sheet_headers": actual_primary_headers,
        "missing_required_primary_sheet_headers": missing_primary_sheet_headers,
        "workbook_validation_enabled": workbook_validation_enabled,
        "status": status,
        "warnings": warnings,
        "submission_readiness_summary": submission_readiness_summary,
    }


def evaluate_export_contract_gate(
    *,
    donor_id: str,
    toc_payload: Dict[str, Any],
    policy_mode: str,
    workbook_sheetnames: Optional[Iterable[str]] = None,
    workbook_primary_sheet_headers: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    contract = evaluate_export_contract(
        donor_id=donor_id,
        toc_payload=toc_payload,
        workbook_sheetnames=workbook_sheetnames,
        workbook_primary_sheet_headers=workbook_primary_sheet_headers,
    )
    mode = normalize_export_contract_policy_mode(policy_mode)
    contract_status = str(contract.get("status") or "warning").lower()
    missing_required_sections = list(contract.get("missing_required_sections") or [])
    missing_required_sheets = list(contract.get("missing_required_sheets") or [])
    missing_primary_sheet_headers = list(contract.get("missing_required_primary_sheet_headers") or [])
    warnings = [str(item) for item in (contract.get("warnings") or []) if str(item or "").strip()]
    reasons = list(warnings)
    if not reasons and contract_status != "pass":
        reasons.append("export_contract_warning")

    if mode == "off":
        passed = True
        blocking = False
        summary = "policy_off"
        reasons = []
        risk_level = "low"
    else:
        passed = contract_status == "pass"
        blocking = mode == "strict" and not passed
        summary = "export_contract_ok" if passed else ",".join(reasons)
        if missing_required_sections:
            risk_level = "high"
        elif missing_primary_sheet_headers:
            risk_level = "high"
        elif missing_required_sheets:
            risk_level = "medium"
        elif passed:
            risk_level = "low"
        else:
            risk_level = "medium"

    gate = dict(contract)
    gate.update(
        {
            "mode": mode,
            "passed": passed,
            "blocking": blocking,
            "go_ahead": not blocking,
            "summary": summary,
            "reasons": reasons,
            "risk_level": risk_level,
        }
    )
    return gate
