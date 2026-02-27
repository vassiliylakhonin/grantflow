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
            "citation_confidence": 0.82,
        }
    ]


def _sample_critic_findings():
    return [
        {
            "finding_id": "finding-123",
            "status": "acknowledged",
            "severity": "high",
            "section": "toc",
            "code": "TOC_SCHEMA_INVALID",
            "message": "ToC schema contract mismatch.",
            "fix_hint": "Revise objective structure.",
            "version_id": "toc_v2",
            "source": "rules",
        }
    ]


def _sample_review_comments():
    return [
        {
            "comment_id": "comment-123",
            "status": "resolved",
            "section": "toc",
            "author": "reviewer-1",
            "message": "Adjusted objective wording and assumptions.",
            "version_id": "toc_v2",
            "linked_finding_id": "finding-123",
            "ts": "2026-02-25T10:00:00Z",
        }
    ]


def test_word_export_includes_citation_traceability_section():
    toc_draft = {
        "toc": {
            "brief": "Sample ToC brief",
            "objectives": [{"title": "Obj 1", "description": "Desc", "citation": "usaid_ads201"}],
        }
    }
    content = build_docx_from_toc(
        toc_draft,
        "usaid",
        citations=_sample_citations(),
        critic_findings=_sample_critic_findings(),
        review_comments=_sample_review_comments(),
    )
    doc = Document(BytesIO(content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Citation Traceability" in text
    assert "USAID ADS 201 p.12" in text
    assert "Official indicator guidance excerpt" in text
    assert "conf 0.82" in text
    assert "Critic Findings" in text
    assert "TOC_SCHEMA_INVALID" in text
    assert "Review Comments" in text
    assert "Adjusted objective wording and assumptions." in text


def test_word_export_uses_donor_specific_sections_for_usaid_eu_worldbank():
    usaid_toc = {
        "toc": {
            "project_goal": "Improve civic services",
            "development_objectives": [
                {
                    "do_id": "DO1",
                    "description": "Improved digital delivery",
                    "intermediate_results": [
                        {
                            "ir_id": "IR1.1",
                            "description": "Civil service capacity strengthened",
                            "outputs": [
                                {
                                    "output_id": "O1.1.1",
                                    "description": "Training delivered",
                                    "indicators": [
                                        {
                                            "indicator_code": "EG.1-1",
                                            "name": "Officials trained",
                                            "target": "300",
                                            "justification": "Capacity milestone",
                                            "citation": "USAID ADS 201 p.12",
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
            "critical_assumptions": ["Government commitment remains stable"],
        }
    }
    eu_toc = {
        "toc": {"overall_objective": {"objective_id": "OO1", "title": "Digital governance", "rationale": "EU fit"}}
    }
    wb_toc = {
        "toc": {
            "objectives": [
                {"objective_id": "PDO1", "title": "Service delivery quality", "description": "Better outcomes"}
            ]
        }
    }

    usaid_doc = Document(BytesIO(build_docx_from_toc(usaid_toc, "usaid")))
    eu_doc = Document(BytesIO(build_docx_from_toc(eu_toc, "eu")))
    wb_doc = Document(BytesIO(build_docx_from_toc(wb_toc, "worldbank")))
    usaid_text = "\n".join(p.text for p in usaid_doc.paragraphs)
    eu_text = "\n".join(p.text for p in eu_doc.paragraphs)
    wb_text = "\n".join(p.text for p in wb_doc.paragraphs)

    assert "USAID Results Framework" in usaid_text
    assert "Critical Assumptions" in usaid_text
    assert "EU Intervention Logic" in eu_text
    assert "Overall Objective" in eu_text
    assert "World Bank Results Framework" in wb_text
    assert "PDO1" in wb_text


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
    content = build_xlsx_from_logframe(
        logframe_draft,
        "usaid",
        citations=_sample_citations(),
        critic_findings=_sample_critic_findings(),
        review_comments=_sample_review_comments(),
    )
    wb = load_workbook(BytesIO(content))
    assert "LogFrame" in wb.sheetnames
    assert "Citations" in wb.sheetnames
    assert "Critic Findings" in wb.sheetnames
    assert "Review Comments" in wb.sheetnames

    ws = wb["Citations"]
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0][:5] == ("Stage", "Type", "Used For", "Label", "Confidence")
    assert any(row[3] == "USAID ADS 201 p.12" for row in rows[1:])
    assert any(abs(float(row[4]) - 0.82) < 1e-9 for row in rows[1:] if row[4] is not None)

    findings_rows = list(wb["Critic Findings"].iter_rows(values_only=True))
    assert findings_rows[0][:4] == ("Status", "Severity", "Section", "Code")
    assert any(row[3] == "TOC_SCHEMA_INVALID" for row in findings_rows[1:])

    comments_rows = list(wb["Review Comments"].iter_rows(values_only=True))
    assert comments_rows[0][:4] == ("Status", "Section", "Author", "Message")
    assert any(row[6] == "2026-02-25T10:00:00Z" for row in comments_rows[1:])


def test_excel_export_includes_donor_specific_sheets():
    usaid_toc = {
        "toc": {
            "development_objectives": [
                {
                    "do_id": "DO1",
                    "description": "Improved digital delivery",
                    "intermediate_results": [
                        {
                            "ir_id": "IR1.1",
                            "description": "Civil service capacity strengthened",
                            "outputs": [
                                {
                                    "output_id": "O1.1.1",
                                    "description": "Training delivered",
                                    "indicators": [
                                        {
                                            "indicator_code": "EG.1-1",
                                            "name": "Officials trained",
                                            "target": "300",
                                            "justification": "Capacity milestone",
                                            "citation": "USAID ADS 201 p.12",
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    eu_toc = {
        "toc": {"overall_objective": {"objective_id": "OO1", "title": "Digital governance", "rationale": "EU fit"}}
    }
    wb_toc = {
        "toc": {
            "objectives": [
                {"objective_id": "PDO1", "title": "Service delivery quality", "description": "Better outcomes"}
            ]
        }
    }

    usaid_wb = load_workbook(BytesIO(build_xlsx_from_logframe({"indicators": []}, "usaid", toc_draft=usaid_toc)))
    eu_wb = load_workbook(BytesIO(build_xlsx_from_logframe({"indicators": []}, "eu", toc_draft=eu_toc)))
    wb_wb = load_workbook(BytesIO(build_xlsx_from_logframe({"indicators": []}, "worldbank", toc_draft=wb_toc)))

    assert "USAID_RF" in usaid_wb.sheetnames
    assert "EU_Intervention" in eu_wb.sheetnames
    assert "WB_Results" in wb_wb.sheetnames

    usaid_rows = list(usaid_wb["USAID_RF"].iter_rows(values_only=True))
    assert usaid_rows[0][0] == "DO ID"
    assert any(row[0] == "DO1" and row[6] == "EG.1-1" for row in usaid_rows[1:])
