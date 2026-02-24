from io import BytesIO

from docx import Document
from openpyxl import load_workbook

from grantflow.exporters.excel_builder import build_xlsx_from_logframe
from grantflow.exporters.word_builder import build_docx_from_toc


def _sample_citations():
    return [
        {
            "stage": "mel",
            "citation_type": "rag_result",
            "namespace": "usaid_ads201",
            "source": "/tmp/usaid_guide.pdf",
            "page": 12,
            "chunk": 3,
            "chunk_id": "usaid_ads201_p12_c0",
            "used_for": "EG.3.2-1",
            "label": "USAID ADS 201 p.12",
            "excerpt": "Official indicator guidance excerpt",
        }
    ]


def test_word_export_includes_citation_traceability_section():
    toc_draft = {
        "toc": {
            "brief": "Sample ToC brief",
            "objectives": [{"title": "Obj 1", "description": "Desc", "citation": "usaid_ads201"}],
        }
    }
    content = build_docx_from_toc(toc_draft, "usaid", citations=_sample_citations())
    doc = Document(BytesIO(content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Citation Traceability" in text
    assert "USAID ADS 201 p.12" in text
    assert "Official indicator guidance excerpt" in text


def test_excel_export_includes_citations_sheet():
    logframe_draft = {
        "indicators": [
            {
                "indicator_id": "IND_001",
                "name": "Indicator A",
                "justification": "Test",
                "citation": "USAID ADS 201 p.12",
                "baseline": "0",
                "target": "100",
            }
        ]
    }
    content = build_xlsx_from_logframe(logframe_draft, "usaid", citations=_sample_citations())
    wb = load_workbook(BytesIO(content))
    assert "LogFrame" in wb.sheetnames
    assert "Citations" in wb.sheetnames

    ws = wb["Citations"]
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0][:4] == ("Stage", "Type", "Used For", "Label")
    assert any(row[3] == "USAID ADS 201 p.12" for row in rows[1:])
