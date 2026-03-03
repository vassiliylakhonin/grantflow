from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from grantflow.exporters.template_profile import (
    TEMPLATE_DISPLAY_NAMES,
    build_export_template_profile,
    normalize_export_template_key,
)

DONOR_DOCX_EXPECTED_HEADINGS: dict[str, list[str]] = {
    "usaid": ["USAID Results Framework", "Project Goal", "Development Objectives", "Critical Assumptions"],
    "eu": ["EU Intervention Logic", "Overall Objective", "Specific Objectives", "Expected Outcomes"],
    "worldbank": [
        "World Bank Results Framework",
        "Project Development Objective (PDO)",
        "Objectives",
        "Results Chain",
    ],
}

DONOR_XLSX_REQUIRED_SHEETS: dict[str, list[str]] = {
    "usaid": ["LogFrame", "USAID_RF", "Template Meta"],
    "eu": ["LogFrame", "EU_Intervention", "EU_Assumptions_Risks", "Template Meta"],
    "worldbank": ["LogFrame", "WB_Results", "Template Meta"],
}

DONOR_XLSX_PRIMARY_SHEET: dict[str, str] = {
    "usaid": "USAID_RF",
    "eu": "EU_Intervention",
    "worldbank": "WB_Results",
}

DONOR_XLSX_PRIMARY_HEADERS: dict[str, list[str]] = {
    "usaid": ["DO ID", "DO Description", "IR ID", "IR Description"],
    "eu": ["Level", "ID", "Title", "Description"],
    "worldbank": ["Level", "ID", "Title", "Description"],
}
EXPORT_CONTRACT_POLICY_MODES = {"off", "warn", "strict"}


def normalize_export_contract_policy_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "warn").strip().lower()
    if mode not in EXPORT_CONTRACT_POLICY_MODES:
        return "warn"
    return mode


def normalize_toc_payload(toc_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(toc_payload, dict):
        return {}
    toc_root = toc_payload.get("toc")
    if isinstance(toc_root, dict):
        return toc_root
    return toc_payload


def evaluate_export_contract(
    *,
    donor_id: str,
    toc_payload: Dict[str, Any],
    workbook_sheetnames: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    toc_root = normalize_toc_payload(toc_payload if isinstance(toc_payload, dict) else {})
    donor_key = normalize_export_template_key(donor_id)
    profile = build_export_template_profile(donor_id=donor_id, toc_payload=toc_root)

    required_sections = list(profile.get("required_sections") or [])
    missing_required_sections = list(profile.get("missing_sections") or [])
    present_required_sections = list(profile.get("present_sections") or [])

    required_sheets = list(DONOR_XLSX_REQUIRED_SHEETS.get(donor_key, []))
    workbook_validation_enabled = workbook_sheetnames is not None
    actual_sheets = [str(x) for x in (workbook_sheetnames or [])] if workbook_validation_enabled else []
    missing_required_sheets = [name for name in required_sheets if name not in actual_sheets] if workbook_validation_enabled else []

    expected_docx_headings = list(DONOR_DOCX_EXPECTED_HEADINGS.get(donor_key, []))
    primary_sheet = DONOR_XLSX_PRIMARY_SHEET.get(donor_key)
    primary_headers = list(DONOR_XLSX_PRIMARY_HEADERS.get(donor_key, []))

    status = "pass" if not missing_required_sections and not missing_required_sheets else "warning"
    warnings: list[str] = []
    if missing_required_sections:
        warnings.append("missing_required_toc_sections")
    if workbook_validation_enabled and missing_required_sheets:
        warnings.append("missing_required_workbook_sheets")

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
        "workbook_validation_enabled": workbook_validation_enabled,
        "status": status,
        "warnings": warnings,
    }


def evaluate_export_contract_gate(
    *,
    donor_id: str,
    toc_payload: Dict[str, Any],
    policy_mode: str,
    workbook_sheetnames: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    contract = evaluate_export_contract(
        donor_id=donor_id,
        toc_payload=toc_payload,
        workbook_sheetnames=workbook_sheetnames,
    )
    mode = normalize_export_contract_policy_mode(policy_mode)
    contract_status = str(contract.get("status") or "warning").lower()
    missing_required_sections = list(contract.get("missing_required_sections") or [])
    missing_required_sheets = list(contract.get("missing_required_sheets") or [])
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
