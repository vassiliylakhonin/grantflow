# grantflow/exporters/excel_builder.py

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def _autosize_columns(ws) -> None:
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 60)
        ws.column_dimensions[column].width = adjusted_width


def _normalize_donor_id(donor_id: str) -> str:
    return str(donor_id or "").strip().lower()


def _toc_root(payload: Dict[str, Any]) -> Dict[str, Any]:
    toc = payload.get("toc")
    if isinstance(toc, dict):
        return toc
    return payload if isinstance(payload, dict) else {}


def _add_citations_sheet(wb: Workbook, citations: list[Dict[str, Any]]) -> None:
    if not citations:
        return
    ws = wb.create_sheet("Citations")
    headers = [
        "Stage",
        "Type",
        "Used For",
        "Label",
        "Confidence",
        "Namespace",
        "Source",
        "Page",
        "Chunk",
        "Chunk ID",
        "Excerpt",
    ]
    ws.append(headers)
    for c in citations:
        ws.append(
            [
                c.get("stage", ""),
                c.get("citation_type", ""),
                c.get("used_for", ""),
                c.get("label", ""),
                c.get("citation_confidence", ""),
                c.get("namespace", ""),
                c.get("source", ""),
                c.get("page", ""),
                c.get("chunk", ""),
                c.get("chunk_id", ""),
                (c.get("excerpt", "") or "")[:500],
            ]
        )
    _autosize_columns(ws)


def _add_critic_findings_sheet(wb: Workbook, critic_findings: list[Dict[str, Any]]) -> None:
    if not critic_findings:
        return
    ws = wb.create_sheet("Critic Findings")
    headers = [
        "Status",
        "Severity",
        "Section",
        "Code",
        "Message",
        "Fix Hint",
        "Version ID",
        "Finding ID",
        "Source",
    ]
    ws.append(headers)
    for f in critic_findings:
        ws.append(
            [
                f.get("status", ""),
                f.get("severity", ""),
                f.get("section", ""),
                f.get("code", ""),
                f.get("message", ""),
                f.get("fix_hint", ""),
                f.get("version_id", ""),
                f.get("finding_id", ""),
                f.get("source", ""),
            ]
        )
    _autosize_columns(ws)


def _add_review_comments_sheet(wb: Workbook, review_comments: list[Dict[str, Any]]) -> None:
    if not review_comments:
        return
    ws = wb.create_sheet("Review Comments")
    headers = ["Status", "Section", "Author", "Message", "Version ID", "Linked Finding ID", "Timestamp", "Comment ID"]
    ws.append(headers)
    for c in review_comments:
        ws.append(
            [
                c.get("status", ""),
                c.get("section", ""),
                c.get("author", ""),
                c.get("message", ""),
                c.get("version_id", ""),
                c.get("linked_finding_id", ""),
                c.get("ts", ""),
                c.get("comment_id", ""),
            ]
        )
    _autosize_columns(ws)


def _apply_table_header(ws, headers: list[str]) -> Border:
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    return thin_border


def _add_usaid_results_sheet(wb: Workbook, toc_payload: Dict[str, Any]) -> None:
    toc = _toc_root(toc_payload)
    ws = wb.create_sheet("USAID_RF")
    headers = [
        "DO ID",
        "DO Description",
        "IR ID",
        "IR Description",
        "Output ID",
        "Output Description",
        "Indicator Code",
        "Indicator Name",
        "Target",
        "Justification",
        "Citation",
    ]
    thin_border = _apply_table_header(ws, headers)

    row_idx = 2
    for do in toc.get("development_objectives") or []:
        if not isinstance(do, dict):
            continue
        do_id = do.get("do_id", "")
        do_desc = do.get("description", "")
        for ir in do.get("intermediate_results") or []:
            if not isinstance(ir, dict):
                continue
            ir_id = ir.get("ir_id", "")
            ir_desc = ir.get("description", "")
            for output in ir.get("outputs") or []:
                if not isinstance(output, dict):
                    continue
                output_id = output.get("output_id", "")
                output_desc = output.get("description", "")
                indicators = output.get("indicators") or []
                if not isinstance(indicators, list) or not indicators:
                    ws.append(
                        [
                            do_id,
                            do_desc,
                            ir_id,
                            ir_desc,
                            output_id,
                            output_desc,
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )
                    for col in range(1, len(headers) + 1):
                        ws.cell(row=row_idx, column=col).border = thin_border
                    row_idx += 1
                    continue
                for ind in indicators:
                    if not isinstance(ind, dict):
                        continue
                    ws.append(
                        [
                            do_id,
                            do_desc,
                            ir_id,
                            ir_desc,
                            output_id,
                            output_desc,
                            ind.get("indicator_code", ""),
                            ind.get("name", ""),
                            ind.get("target", ""),
                            ind.get("justification", ""),
                            ind.get("citation", ""),
                        ]
                    )
                    for col in range(1, len(headers) + 1):
                        ws.cell(row=row_idx, column=col).border = thin_border
                    row_idx += 1
    _autosize_columns(ws)


def _add_eu_results_sheet(wb: Workbook, toc_payload: Dict[str, Any]) -> None:
    toc = _toc_root(toc_payload)
    ws = wb.create_sheet("EU_Intervention")
    headers = ["Objective ID", "Title", "Rationale"]
    thin_border = _apply_table_header(ws, headers)
    overall = toc.get("overall_objective") if isinstance(toc, dict) else None
    if isinstance(overall, dict):
        ws.append([overall.get("objective_id", ""), overall.get("title", ""), overall.get("rationale", "")])
    else:
        ws.append(["", "", ""])
    for col in range(1, len(headers) + 1):
        ws.cell(row=2, column=col).border = thin_border
    _autosize_columns(ws)


def _add_worldbank_results_sheet(wb: Workbook, toc_payload: Dict[str, Any]) -> None:
    toc = _toc_root(toc_payload)
    ws = wb.create_sheet("WB_Results")
    headers = ["Objective ID", "Title", "Description"]
    thin_border = _apply_table_header(ws, headers)
    row_idx = 2
    objectives = toc.get("objectives") if isinstance(toc, dict) else None
    if isinstance(objectives, list) and objectives:
        for obj in objectives:
            if not isinstance(obj, dict):
                continue
            ws.append([obj.get("objective_id", ""), obj.get("title", ""), obj.get("description", "")])
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col).border = thin_border
            row_idx += 1
    else:
        ws.append(["", "", ""])
        for col in range(1, len(headers) + 1):
            ws.cell(row=2, column=col).border = thin_border
    _autosize_columns(ws)


def build_xlsx_from_logframe(
    logframe_draft: Dict[str, Any],
    donor_id: str,
    toc_draft: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """Конвертирует LogFrame draft в форматированный .xlsx."""
    wb = Workbook()
    ws = wb.active
    ws.title = "LogFrame"

    headers = ["Indicator ID", "Name", "Justification", "Citation", "Baseline", "Target"]
    thin_border = _apply_table_header(ws, headers)

    indicators = logframe_draft.get("indicators", []) if logframe_draft else []
    for row, ind in enumerate(indicators, 2):
        ws.cell(row=row, column=1, value=ind.get("indicator_id", "")).border = thin_border
        ws.cell(row=row, column=2, value=ind.get("name", "")).border = thin_border
        ws.cell(row=row, column=3, value=ind.get("justification", "")).border = thin_border
        ws.cell(row=row, column=4, value=ind.get("citation", "")).border = thin_border
        ws.cell(row=row, column=5, value=ind.get("baseline", "TBD")).border = thin_border
        ws.cell(row=row, column=6, value=ind.get("target", "TBD")).border = thin_border

    donor_key = _normalize_donor_id(donor_id)
    toc_payload = toc_draft if isinstance(toc_draft, dict) else {}
    if not toc_payload:
        toc_payload = logframe_draft if isinstance(logframe_draft, dict) else {}
    if donor_key == "usaid":
        _add_usaid_results_sheet(wb, toc_payload)
    elif donor_key == "eu":
        _add_eu_results_sheet(wb, toc_payload)
    elif donor_key == "worldbank":
        _add_worldbank_results_sheet(wb, toc_payload)

    _autosize_columns(ws)
    _add_citations_sheet(wb, citations or logframe_draft.get("citations") or [])
    _add_critic_findings_sheet(wb, critic_findings or [])
    _add_review_comments_sheet(wb, review_comments or [])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()


def save_xlsx_to_file(
    logframe_draft: Dict[str, Any],
    donor_id: str,
    output_path: str,
    toc_draft: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Сохраняет .xlsx на диск."""
    content = build_xlsx_from_logframe(
        logframe_draft,
        donor_id,
        toc_draft=toc_draft,
        citations=citations,
        critic_findings=critic_findings,
        review_comments=review_comments,
    )
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path
