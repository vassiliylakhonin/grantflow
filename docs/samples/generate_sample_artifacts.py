from __future__ import annotations

import json
from pathlib import Path

from grantflow.exporters.excel_builder import save_xlsx_to_file
from grantflow.exporters.word_builder import save_docx_to_file


def build_sample_payload() -> dict:
    donor_id = "usaid"
    toc_draft = {
        "toc": {
            "brief": (
                "This sanitized sample illustrates the structure of a donor-aligned draft for a public-sector "
                "AI capacity strengthening program. It is not a real proposal submission."
            ),
            "objectives": [
                {
                    "title": "Strengthen institutional capacity for responsible AI use in government workflows",
                    "description": (
                        "Participating agencies adopt supervised AI use practices, governance guidance, and "
                        "pilot workflow improvements tied to service quality and administrative efficiency."
                    ),
                    "citation": "Seed corpus guidance + contextual public administration references",
                },
                {
                    "title": "Improve civil servant competencies for applied AI in priority functions",
                    "description": (
                        "Civil servants complete training and applied labs covering AI literacy, safe use, "
                        "oversight, and workflow design in policy and service delivery contexts."
                    ),
                    "citation": "Training design and competency framework references",
                },
            ],
        },
        "indicators": [
            {
                "name": "% of participating agencies applying approved AI SOPs in pilot workflows",
                "justification": "Tracks institutional adoption beyond training attendance.",
            },
            {
                "name": "% of trained participants scoring above competency threshold in post-test",
                "justification": "Captures competency improvement among trained cohorts.",
            },
        ],
    }
    logframe_draft = {
        "indicators": [
            {
                "indicator_id": "DO-1",
                "name": "% of participating agencies applying approved AI SOPs in pilot workflows",
                "justification": "Measures institutionalization of AI governance and supervised use.",
                "citation": "WB/USAID-style results and SOP adoption verification guidance",
                "baseline": 0,
                "target": "60% by endline",
            },
            {
                "indicator_id": "IR1-1",
                "name": "% of trained participants scoring above competency threshold in post-test",
                "justification": "Measures immediate training outcome before workflow adoption.",
                "citation": "Training assessment methodology note",
                "baseline": "TBD (baseline cohort)",
                "target": "75%",
            },
            {
                "indicator_id": "OUT-1",
                "name": "# civil servants completing cohort modules",
                "justification": "Tracks delivery volume and program reach.",
                "citation": "Attendance and LMS completion records",
                "baseline": 0,
                "target": "600-1000",
            },
        ]
    }
    citations = [
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "used_for": "objective",
            "label": "USAID Program Cycle / Results Logic (seed)",
            "namespace": "usaid_ads201",
            "source": "01_usaid_donor_policy_ads_program_cycle_seed.pdf",
            "page": 2,
            "chunk": 1,
            "chunk_id": "usaid-seed-ads201-p2-c1",
            "citation_confidence": 0.84,
            "confidence_threshold": 0.32,
            "excerpt": "Results design should link activities, outputs, intermediate results, and development objectives.",
        },
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "used_for": "objective",
            "label": "Civil Service AI Competency Framework (seed)",
            "namespace": "usaid_ads201",
            "source": "04_civil_service_ai_competency_framework_seed.pdf",
            "page": 3,
            "chunk": 0,
            "chunk_id": "usaid-seed-competency-p3-c0",
            "citation_confidence": 0.79,
            "confidence_threshold": 0.32,
            "excerpt": "Competency pathways should combine foundational literacy, supervised application, and governance awareness.",
        },
        {
            "stage": "mel",
            "citation_type": "rag_result",
            "used_for": "indicator_selection",
            "label": "Results framework and M&E guidance (seed)",
            "namespace": "usaid_ads201",
            "source": "01_usaid_donor_policy_ads_program_cycle_seed.pdf",
            "page": 4,
            "chunk": 2,
            "chunk_id": "usaid-seed-ads201-p4-c2",
            "citation_confidence": 0.8,
            "excerpt": "Indicators should be tied to decision-making and feasible means of verification.",
        },
    ]
    critic_findings = [
        {
            "finding_id": "finding-001",
            "status": "resolved",
            "severity": "low",
            "section": "toc",
            "code": "OBJECTIVE_SPECIFICITY",
            "message": "Objective wording was broad; revised to emphasize institutional adoption and supervised use.",
            "fix_hint": "Keep measurable adoption language in objective and align with indicator set.",
            "version_id": "toc-v2",
            "source": "llm",
            "label": "OBJECTIVE_SPECIFICITY",
        },
        {
            "finding_id": "finding-002",
            "status": "open",
            "severity": "medium",
            "section": "logframe",
            "code": "BASELINE_TARGET_MISSING",
            "message": "Baseline methodology is described, but baseline values for all participating agencies are still TBD.",
            "fix_hint": "Add baseline plan timeline and agency coverage assumptions before submission.",
            "version_id": "logframe-v1",
            "source": "llm",
            "label": "BASELINE_TARGET_MISSING",
        },
    ]
    review_comments = [
        {
            "comment_id": "comment-001",
            "status": "resolved",
            "section": "toc",
            "author": "program_lead",
            "message": "Clarify institutional adoption vs individual training outcomes in the objective statement.",
            "version_id": "toc-v1",
            "linked_finding_id": "finding-001",
            "ts": "2026-02-26T10:15:00Z",
        },
        {
            "comment_id": "comment-002",
            "status": "open",
            "section": "logframe",
            "author": "mel_advisor",
            "message": "Need baseline collection schedule and source owners before finalizing targets.",
            "version_id": "logframe-v1",
            "linked_finding_id": "finding-002",
            "ts": "2026-02-26T10:24:00Z",
        },
    ]
    return {
        "donor_id": donor_id,
        "toc_draft": toc_draft,
        "logframe_draft": logframe_draft,
        "citations": citations,
        "critic_findings": critic_findings,
        "review_comments": review_comments,
    }


def main() -> int:
    samples_dir = Path(__file__).resolve().parent
    samples_dir.mkdir(parents=True, exist_ok=True)

    payload = build_sample_payload()
    donor_id = payload["donor_id"]

    save_docx_to_file(
        payload["toc_draft"],
        donor_id,
        str(samples_dir / "grantflow-sample-toc-review-package.docx"),
        citations=payload["citations"],
        critic_findings=payload["critic_findings"],
        review_comments=payload["review_comments"],
    )
    save_xlsx_to_file(
        payload["logframe_draft"],
        donor_id,
        str(samples_dir / "grantflow-sample-logframe-review-package.xlsx"),
        citations=payload["citations"],
        critic_findings=payload["critic_findings"],
        review_comments=payload["review_comments"],
    )

    (samples_dir / "grantflow-sample-export-payload.json").write_text(
        json.dumps(
            {
                "payload": {
                    "state": {
                        "toc_draft": payload["toc_draft"],
                        "logframe_draft": payload["logframe_draft"],
                        "citations": payload["citations"],
                        "critic_notes": {"fatal_flaws": payload["critic_findings"]},
                    },
                    "critic_findings": payload["critic_findings"],
                    "review_comments": payload["review_comments"],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
