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


def build_xlsx_from_logframe(
    logframe_draft: Dict[str, Any],
    donor_id: str,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """Конвертирует LogFrame draft в форматированный .xlsx."""
    wb = Workbook()
    ws = wb.active
    ws.title = "LogFrame"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin")
    )

    headers = ["Indicator ID", "Name", "Justification", "Citation", "Baseline", "Target"]
    ws.append(headers)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    indicators = logframe_draft.get("indicators", []) if logframe_draft else []
    for row, ind in enumerate(indicators, 2):
        ws.cell(row=row, column=1, value=ind.get("indicator_id", "")).border = thin_border
        ws.cell(row=row, column=2, value=ind.get("name", "")).border = thin_border
        ws.cell(row=row, column=3, value=ind.get("justification", "")).border = thin_border
        ws.cell(row=row, column=4, value=ind.get("citation", "")).border = thin_border
        ws.cell(row=row, column=5, value=ind.get("baseline", "TBD")).border = thin_border
        ws.cell(row=row, column=6, value=ind.get("target", "TBD")).border = thin_border

    _autosize_columns(ws)
    _add_citations_sheet(wb, citations or logframe_draft.get("citations") or [])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()


def save_xlsx_to_file(
    logframe_draft: Dict[str, Any],
    donor_id: str,
    output_path: str,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Сохраняет .xlsx на диск."""
    content = build_xlsx_from_logframe(logframe_draft, donor_id, citations=citations)
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path
