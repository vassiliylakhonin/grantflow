from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from grantflow.api.idempotency_store_facade import (
    _get_job,
    _ingest_inventory,
    _list_jobs,
)
from grantflow.api.orchestrator_service import (
    _configured_export_require_grounded_gate_pass,
    _evaluate_export_contract_gate,
    _evaluate_export_grounding_policy,
    _xlsx_contract_validation_context,
)
from grantflow.api.review_service import (
    _hitl_history_payload,
    _normalize_critic_fatal_flaws_for_job,
    _normalize_review_comments_for_job,
)
from grantflow.api.export_helpers import (
    _dead_letter_queue_csv_text,
    _extract_export_grounding_gate,
    _extract_export_runtime_grounded_quality_gate,
    _hitl_history_csv_text,
    _job_comments_csv_text,
    _job_events_csv_text,
    _portfolio_export_response,
    _resolve_export_inputs,
)
from grantflow.api.filters import _validated_filter_token
from grantflow.api.public_views import (
    REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
    REVIEW_WORKFLOW_STATE_FILTER_VALUES,
    public_ingest_inventory_csv_text,
    public_ingest_inventory_payload,
    public_job_comments_payload,
    public_job_events_payload,
    public_job_export_payload,
    public_job_review_workflow_csv_text,
    public_job_review_workflow_payload,
    public_job_review_workflow_sla_csv_text,
    public_job_review_workflow_sla_hotspots_csv_text,
    public_job_review_workflow_sla_hotspots_payload,
    public_job_review_workflow_sla_hotspots_trends_csv_text,
    public_job_review_workflow_sla_hotspots_trends_payload,
    public_job_review_workflow_sla_payload,
    public_job_review_workflow_sla_trends_csv_text,
    public_job_review_workflow_sla_trends_payload,
    public_job_review_workflow_trends_csv_text,
    public_job_review_workflow_trends_payload,
    public_portfolio_metrics_csv_text,
    public_portfolio_metrics_payload,
    public_portfolio_quality_csv_text,
    public_portfolio_quality_payload,
    public_portfolio_review_workflow_csv_text,
    public_portfolio_review_workflow_payload,
    public_portfolio_review_workflow_sla_csv_text,
    public_portfolio_review_workflow_sla_hotspots_csv_text,
    public_portfolio_review_workflow_sla_hotspots_payload,
    public_portfolio_review_workflow_sla_hotspots_trends_csv_text,
    public_portfolio_review_workflow_sla_hotspots_trends_payload,
    public_portfolio_review_workflow_sla_payload,
    public_portfolio_review_workflow_sla_trends_csv_text,
    public_portfolio_review_workflow_sla_trends_payload,
    public_portfolio_review_workflow_trends_csv_text,
    public_portfolio_review_workflow_trends_payload,
)
from grantflow.api.schemas import ExportRequest, JobExportPayloadPublicResponse
from grantflow.api.security import require_api_key_if_configured
from grantflow.api.tenant import (
    _ensure_job_tenant_read_access,
    _filter_jobs_by_tenant,
    _job_donor_id,
    _job_tenant_id,
    _resolve_tenant_id,
)
from grantflow.api.routers import exports_router
from grantflow.api.queue_admin_service import _redis_queue_admin_runner
from grantflow.exporters.donor_contracts import evaluate_export_contract
from grantflow.exporters.toc_normalization import normalize_toc_for_export
from grantflow.core.evaluation_rfq import KATCH_EVALUATION_RFQ_PROFILE


def _annex_slug(value: object, *, fallback: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return token or fallback


def _attachment_source_path(row: dict) -> str:
    for key in ("source_path", "staged_file_path", "local_path", "file_path", "attachment_path"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _safe_attachment_export_name(*, index: int, attachment: str, source_path: str) -> str:
    source = Path(source_path)
    suffix = source.suffix if source.suffix else ""
    stem = _annex_slug(attachment or source.stem, fallback=f"attachment_{index}")
    return f"{index:02d}_{stem}{suffix}"


def _evaluation_rfq_annex_pack_artifacts(*, donor_id: str, toc_draft: dict, export_contract: dict) -> dict[str, bytes]:
    contract = evaluate_export_contract(donor_id=donor_id, toc_payload=toc_draft)
    if str(contract.get("template_key") or "") != "evaluation_rfq":
        return {}

    toc_root = toc_draft.get("toc") if isinstance(toc_draft.get("toc"), dict) else toc_draft
    if not isinstance(toc_root, dict):
        toc_root = {}
    submission_rows = [row for row in (toc_root.get("submission_package_checklist") or []) if isinstance(row, dict)]
    attachment_rows = [row for row in (toc_root.get("attachment_manifest") or []) if isinstance(row, dict)]
    compliance_rows = [row for row in (toc_root.get("compliance_matrix") or []) if isinstance(row, dict)]
    summary = contract.get("submission_readiness_summary") if isinstance(contract, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    attachment_file_validation = {
        "attached_file_count": 0,
        "missing_ready_file_count": 0,
        "status_file_mismatch_count": 0,
    }
    normalized_attachment_rows: list[dict] = []

    manifest = {
        "proposal_mode": "evaluation_rfq",
        "template_key": contract.get("template_key"),
        "template_display_name": contract.get("template_display_name"),
        "donor_id": donor_id,
        "submission_readiness_summary": summary,
        "attachment_file_validation": attachment_file_validation,
        "export_contract_status": export_contract.get("status"),
        "export_contract_mode": export_contract.get("mode"),
        "export_contract_summary": export_contract.get("summary"),
        "submission_package_checklist": submission_rows,
        "attachment_manifest": normalized_attachment_rows,
        "compliance_matrix": compliance_rows,
    }
    lines = [
        "# Annex Packer Summary",
        "",
        f"- Donor: `{donor_id}`",
        f"- Template: `{contract.get('template_key') or '-'}`",
        f"- Submission completeness score: `{summary.get('completeness_score', 0)}`",
        f"- Submission readiness status: `{summary.get('readiness_status') or '-'}`",
        f"- Top submission gap: `{summary.get('top_gap') or '-'}`",
        f"- Export contract status: `{export_contract.get('status') or '-'}`",
        f"- Export contract summary: `{export_contract.get('summary') or '-'}`",
        "",
        "## Submission Package",
    ]
    if submission_rows:
        for row in submission_rows:
            lines.append(
                f"- `{row.get('artifact') or '-'}` | owner=`{row.get('owner') or '-'}` | status=`{row.get('status') or '-'}`"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Attachment Manifest"])
    artifacts: dict[str, bytes] = {}
    package_lines = [
        "# Submission Package Placeholder Structure",
        "",
        "This folder tree is a handoff scaffold for the final procurement-style submission package.",
        "Populate each folder with the final customer-facing files before external submission.",
        "",
    ]
    for idx, row in enumerate(submission_rows, start=1):
        artifact = str(row.get("artifact") or f"artifact_{idx}").strip()
        owner = str(row.get("owner") or "-").strip()
        status = str(row.get("status") or "-").strip()
        notes = str(row.get("notes") or "").strip()
        folder = f"submission_package/{idx:02d}_{_annex_slug(artifact, fallback=f'artifact_{idx}')}"
        artifacts[f"{folder}/README.md"] = (
            "\n".join(
                [
                    f"# {artifact}",
                    "",
                    f"- Owner: `{owner}`",
                    f"- Status: `{status}`",
                    f"- Notes: `{notes or '-'}`",
                    "",
                    "Place the finalized file(s) for this submission artifact in this folder.",
                    "",
                ]
            ).encode("utf-8")
        )
        package_lines.append(f"- `{folder}/` -> `{artifact}`")

    annex_folder = "submission_package/99_attachment_manifest"
    artifacts[f"{annex_folder}/README.md"] = (
        "\n".join(
            [
                "# Attachment Manifest",
                "",
                "Use this folder to stage annexes and support files referenced in the manifest.",
                "",
            ]
        ).encode("utf-8")
    )
    for idx, row in enumerate(attachment_rows, start=1):
        attachment = str(row.get("attachment") or f"attachment_{idx}").strip()
        required_for = str(row.get("required_for") or "-").strip()
        owner = str(row.get("owner") or "-").strip()
        status = str(row.get("status") or "-").strip()
        notes = str(row.get("notes") or "").strip()
        status_token = status.lower()
        source_path = _attachment_source_path(row)
        source_exists = False
        attached_file = False
        mismatch_reason = ""
        file_path = f"{annex_folder}/{idx:02d}_{_annex_slug(attachment, fallback=f'attachment_{idx}')}.md"
        source_display = source_path or "-"
        artifacts[file_path] = (
            "\n".join(
                [
                    f"# {attachment}",
                    "",
                    f"- Required for: `{required_for}`",
                    f"- Owner: `{owner}`",
                    f"- Status: `{status}`",
                    f"- Source path: `{source_display}`",
                    f"- Notes: `{notes or '-'}`",
                    "",
                    "Attach or replace this placeholder with the final annex file if a live source path is not provided.",
                    "",
                ]
            ).encode("utf-8")
        )
        if source_path:
            try:
                source = Path(source_path).expanduser().resolve(strict=True)
            except (FileNotFoundError, OSError):
                source = None
            if source is not None and source.is_file():
                source_exists = True
                export_name = _safe_attachment_export_name(index=idx, attachment=attachment, source_path=str(source))
                binary_path = f"{annex_folder}/files/{export_name}"
                try:
                    artifacts[binary_path] = source.read_bytes()
                    attached_file = True
                except OSError:
                    attached_file = False
        if status_token == "ready" and not attached_file:
            attachment_file_validation["missing_ready_file_count"] += 1
            mismatch_reason = "status_ready_but_file_missing"
        elif attached_file and status_token not in {"ready", "attached", "complete"}:
            attachment_file_validation["status_file_mismatch_count"] += 1
            mismatch_reason = "file_attached_but_status_not_ready"
        if attached_file:
            attachment_file_validation["attached_file_count"] += 1
        normalized_row = dict(row)
        normalized_row["source_path"] = source_display
        normalized_row["source_exists"] = source_exists
        normalized_row["attached_file"] = attached_file
        normalized_row["attachment_file_status"] = (
            "attached" if attached_file else ("missing" if source_path else "not_provided")
        )
        if mismatch_reason:
            normalized_row["attachment_file_warning"] = mismatch_reason
        normalized_attachment_rows.append(normalized_row)
        line = (
            f"- `{attachment}` | required_for=`{required_for}` | owner=`{owner}` | status=`{status or '-'}` "
            f"| file_status=`{normalized_row['attachment_file_status']}`"
        )
        if mismatch_reason:
            line += f" | warning=`{mismatch_reason}`"
        lines.append(line)
    if not attachment_rows:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Attachment File Validation",
            f"- Attached files: `{attachment_file_validation['attached_file_count']}`",
            f"- Ready rows missing files: `{attachment_file_validation['missing_ready_file_count']}`",
            f"- Status/file mismatches: `{attachment_file_validation['status_file_mismatch_count']}`",
            "",
            "## Compliance Matrix",
        ]
    )
    if compliance_rows:
        for row in compliance_rows:
            lines.append(
                f"- `{row.get('requirement') or '-'}` | section=`{row.get('response_section') or '-'}` | status=`{row.get('status') or '-'}`"
            )
    else:
        lines.append("- none")
    artifacts["annex_packer/annex_manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    artifacts["annex_packer/submission_readiness.md"] = ("\n".join(lines) + "\n").encode("utf-8")
    artifacts["submission_package/README.md"] = ("\n".join(package_lines) + "\n").encode("utf-8")
    artifacts["submission_package/package_structure.json"] = (
        json.dumps(
            {
                "proposal_mode": "evaluation_rfq",
                "donor_id": donor_id,
                "folders": sorted([name for name in artifacts if name.startswith("submission_package/")]),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return artifacts


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    safe_headers = [str(item or "-") for item in headers]
    lines = [
        "| " + " | ".join(safe_headers) + " |",
        "| " + " | ".join("---" for _ in safe_headers) + " |",
    ]
    for row in rows:
        safe_row = [str(item or "-") for item in row]
        lines.append("| " + " | ".join(safe_row) + " |")
    return "\n".join(lines)


def _clean_md_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _rfq_file_title(normalized_toc: dict) -> str:
    if str(normalized_toc.get("rfq_profile") or "").strip().lower() == KATCH_EVALUATION_RFQ_PROFILE:
        return "RFQ-2025-001-KATCH-10019"
    return "Evaluation RFQ"


def _dedupe_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        key = " ".join(str(item or "").split()).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(item).strip())
    return out


def _katch_submission_kit_artifacts(normalized_toc: dict) -> dict[str, bytes]:
    rfq_title = "RFQ-2025-001-KATCH-10019"
    methods = [item for item in (normalized_toc.get("methodology_components") or []) if isinstance(item, dict)]
    method_names = {_clean_md_text(item.get("method")).lower() for item in methods}
    has_outcome_harvesting = "outcome harvesting" in method_names
    has_social_media = "social media analysis" in method_names
    has_fgd = "focus group discussions" in method_names
    has_survey = "beneficiary survey" in method_names or "survey of beneficiaries" in method_names
    questions = [str(item).strip() for item in (normalized_toc.get("evaluation_questions") or []) if str(item).strip()]
    katch_milestones = [
        ("Draft Inception Report", "Jul 14, 2025"),
        ("Final Inception Report", "Jul 28, 2025"),
        ("Workshop + Draft Report", "Sep 15, 2025"),
        ("Final Report + Brief", "Sep 30, 2025"),
    ]
    deliverables = _dedupe_ordered(
        [
            "Draft Inception Report with Evaluation Design & Work Plan",
            "Final Inception Report",
            "Bi-weekly progress updates",
            "Virtual workshop/presentation (15 Sep 2025)",
            "Draft Evaluation Report",
            "Final Evaluation Report (English, ≤50 pages, PII-free)",
            "Stand-alone brief (2–3 pages, non-technical audience)",
            "Cleaned datasets and supporting study materials per Winrock requirements",
        ]
    )
    technical_lines = [
        f"# TECHNICAL PROPOSAL ({rfq_title})",
        "",
        "## 1. Organization Information (1 page)",
        "",
        "Legal Name: [Your Organization Name]",
        "Address: [Full legal address]",
        "Authorized Contact: [Name, Title, phone, email]",
        "Registration Status: [Registration number, country]",
        "Legal Status in Central Asia: [If applicable]",
        "[Your Organization] is a [brief type: consulting firm / NGO / research entity] specialized in monitoring, evaluation, and learning (MEL) in multidimensional development projects, including child protection, counter-trafficking in persons (CTIP), migration, and social services systems strengthening. We apply mixed-method and utilization-focused evaluations that generate decision-ready findings for donors and implementing partners.",
        "Annexes attached:",
        "- Business registration certificate",
        "- Latest audited financial statement",
        "",
        "## 2. Analysis and Proposed Approaches / Methodologies (max 5 pages)",
        "",
        "### 2.1 Understanding of the Assignment",
        "",
        "We understand the KATCH Final Assessment as a summative, learning-oriented evaluation to assess:",
        "- relevance,",
        "- effectiveness,",
        "- efficiency,",
        "- sustainability, and",
        "- outcomes of KATCH (Apr 2023–Mar 2026),",
        "with practical recommendations for future programming by Winrock and USDOS.",
        "",
        "### 2.2 Evaluation Approach",
        "",
        "We propose a Theory-Based, RBM-aligned mixed-method evaluation anchored in KATCH’s Theory of Change and Results Framework.",
        "Core principles:",
        "- Utilization-focused: findings structured for direct use by Winrock/USDOS.",
        "- Contribution-oriented: realistic assessment of KATCH contribution to observed change.",
        "- Triangulated evidence: combine qualitative, quantitative, and document-based evidence.",
        "- Do No Harm and trauma-informed practice in all interactions.",
        "",
        "### 2.3 Evaluation Questions",
        "",
        "We will refine RFQ evaluation questions jointly with KATCH during inception. Final questions will remain under five RFQ criteria:",
    ]
    criteria_defaults = ["Relevance", "Effectiveness", "Efficiency", "Sustainability", "Outcomes (including unintended outcomes)"]
    technical_lines.extend([f"- {item}" for item in criteria_defaults])
    if questions:
        technical_lines.extend(["", "Working question set from the current draft context:"])
        technical_lines.extend([f"- {question}" for question in questions])
    technical_lines.extend(["", "### 2.4 Data Collection Methods", ""])
    technical_lines.extend(
        [
            "A) Desk Review",
            "KATCH ToC, Results Framework, MEL Plan, RMP/CPI, quarterly reports",
            "Rapid situational assessment",
            "Micro-grant documentation",
            "Relevant national policy/legal documents",
            "",
            "B) Key Informant Interviews (KIIs)",
            "Semi-structured interviews with:",
            "KATCH field and home office staff",
            "Implementing partners",
            "Government stakeholders (national and subnational)",
            "International actors / donors / CSO representatives",
            "SAG members and Child CTIP Champions (as appropriate)",
            "",
            "C) Focus Group Discussions (FGDs)",
            "FGDs in sampled locations in southern Kazakhstan to gather implementation-level insights, barriers, and sustainability views.",
            "",
            "D) Beneficiary Survey (up to 50 respondents)",
            "Co-designed and administered with experienced local partners to ensure safeguarding and contextual appropriateness.",
            "",
            "E) Outcome Harvesting",
            "Systematic identification and verification of intended and unintended outcomes (positive/negative), with substantiation of KATCH contribution.",
            "",
            "F) Social Media Analysis",
            "Assessment of awareness outputs and engagement through selected social platforms:",
            "content volume and type,",
            "reach and interaction metrics,",
            "repost/share dynamics,",
            "narrative resonance and project recognizability.",
            "",
        ]
    )
    if not has_outcome_harvesting or not has_social_media or not has_fgd or not has_survey:
        technical_lines.extend(
            [
                "Current draft coverage note:",
                f"- Outcome Harvesting present: {'yes' if has_outcome_harvesting else 'expected in final technical response'}",
                f"- Social Media Analysis present: {'yes' if has_social_media else 'expected in final technical response'}",
                f"- Focus Group Discussions present: {'yes' if has_fgd else 'expected in final technical response'}",
                f"- Beneficiary Survey present: {'yes' if has_survey else 'expected in final technical response'}",
                "",
            ]
        )
    technical_lines.extend(
        [
            "### 2.5 Sampling and Coverage",
            "",
            "Sampling will follow feasibility, ethical safeguards, and representativeness across key stakeholder categories listed in RFQ. We will apply purposive sampling plus snowball expansion where required.",
            "",
            "### 2.6 Data Analysis",
            "",
            "Qualitative: thematic coding, framework analysis mapped to evaluation criteria and questions.",
            "Quantitative: descriptive statistics and trend review of available project performance data.",
            "Integrated analysis: triangulation matrix by evaluation question; confidence ratings for key findings (high/medium/low).",
            "",
            "### 2.7 Ethical Considerations and Safeguarding",
            "",
            "We will apply Winrock’s Do No Harm requirements:",
            "voluntary participation and informed consent,",
            "confidentiality and anonymization,",
            "secure data handling,",
            "trauma-informed interview methods,",
            "child safeguarding protocols (approved adult accompaniment where required).",
            "No personally identifiable information (PII) will be included in submitted reports.",
            "",
            "### 2.8 Potential Limitations and Mitigation",
            "",
            "Stakeholder availability constraints → early scheduling + remote alternatives",
            "Sensitive respondent profiles → trauma-informed facilitation + opt-out options",
            "Data quality variability across sites → daily QA, interviewer debriefs, coding calibration",
            "Attribution complexity → contribution framing and evidence-strength grading",
            "",
            "## 3. Work Plan (max 1 page)",
            "",
            "| Phase | Key Activities | Timeline |",
            "| --- | --- | --- |",
            "| Phase I – Engagement & Inception | Kick-off; document review; refined evaluation matrix; tools and sampling; inception report | Jun 30 – Jul 28, 2025 |",
            "| Phase II – Data Collection | KIIs, FGDs, beneficiary survey, social media review, quality checks | Jul 29 – Aug 31, 2025 |",
            "| Phase III – Analysis & Reporting | Analysis, workshop preparation, draft report, revision, final report + brief | Sep 1 – Sep 30, 2025 |",
            "",
            "Milestones aligned to RFQ:",
        ]
    )
    technical_lines.extend([f"- {name}: {date}" for name, date in katch_milestones])
    technical_lines.extend(
        [
            "",
            "## 4. Proposed LOE (1 page)",
            "",
            "| Activity | Team Leader | Evaluation Expert | Data Analyst | Field/Support | Total PD |",
            "| --- | --- | --- | --- | --- | --- |",
            "| Inception & design | 8 | 6 | 2 | 1 | 17 |",
            "| Tool finalization & piloting | 3 | 4 | 2 | 3 | 12 |",
            "| Field data collection oversight | 7 | 8 | 2 | 8 | 25 |",
            "| Data processing & analysis | 5 | 4 | 6 | 2 | 17 |",
            "| Reporting & workshop | 5 | 2 | 2 | 1 | 10 |",
            "| Total person-days | 28 | 24 | 14 | 15 | 81 |",
            "",
            "## 5. Technical Experience & Past Performance (max 2 pages)",
            "",
            "Project 1: [Title, country, year]",
            "Scope: Final evaluation in [TIP/migration/child protection]",
            "Value: [USD]",
            "Client: [Name]",
            "Contact: [Name, phone, email]",
            "",
            "Project 2: [Title, country, year]",
            "Scope: Endline/midline mixed-method assessment in development sector",
            "Value: [USD]",
            "Client: [Name]",
            "Contact: [Name, phone, email]",
            "",
            "Project 3: [Title, country, year]",
            "Scope: Systems-strengthening/performance review for donor-funded project",
            "Value: [USD]",
            "Client: [Name]",
            "Contact: [Name, phone, email]",
            "",
            "(Add real cases from the last 3–5 years.)",
            "",
            "## 6. Personnel and Team Composition",
            "",
            "Team Leader / Evaluation Specialist — [Name]",
            "Master’s in [field] / senior equivalent experience",
            "3+ years in donor-funded evaluations",
            "Expertise in CTIP/child protection/migration evaluations",
            "Fluent English; strong report drafting and stakeholder facilitation",
            "",
            "Evaluation Expert / Analyst — [Name]",
            "Qualitative and quantitative methods",
            "Tool design, interview/FGD facilitation, synthesis and recommendations",
            "",
            "Data Analyst — [Name]",
            "Data management, coding support, descriptive analysis, visualization",
            "",
            "Field Support Team — [Names/roles]",
            "Logistics, scheduling, transcription/translation, consent handling support",
            "",
            "(CVs in Annex; each key CV ≤5 pages.)",
            "",
            "## 7. Deliverables",
            "",
        ]
    )
    technical_lines.extend([f"- {item}" for item in deliverables])

    financial_lines = [
        f"# FINANCIAL PROPOSAL ({rfq_title})",
        "",
        "Currency: USD",
        "Contract Type: Firm Fixed Price",
        "Total Price: 15,000 USD (inclusive of all taxes)",
        "",
        "## A. Budget Table",
        "",
        "| Cost Category | Unit | Qty | Unit Cost (USD) | Total (USD) |",
        "| --- | --- | --- | --- | --- |",
        "| Team Leader professional fee | person-day | 28 | [x] | [ ] |",
        "| Evaluation Expert fee | person-day | 24 | [x] | [ ] |",
        "| Data Analyst fee | person-day | 14 | [x] | [ ] |",
        "| Field support / coordination | lump sum | 1 | [x] | [ ] |",
        "| Travel & per diem | lump sum | 1 | [x] | [ ] |",
        "| Communications (internet/mobile) | lump sum | 1 | [x] | [ ] |",
        "| Software / qualitative analysis tools | lump sum | 1 | [x] | [ ] |",
        "| Printing/supplies | lump sum | 1 | [x] | [ ] |",
        "| Translation/transcription support | lump sum | 1 | [x] | [ ] |",
        "| Grand Total |  |  |  | 15,000 |",
        "",
        "## B. Budget Narrative",
        "",
        "The budget is based on the proposed level of effort, anticipated field coordination requirements across KATCH target regions, data collection and processing needs, and reporting deliverables aligned with RFQ deadlines. Costs are reasonable and sufficient to complete all deliverables to required quality standards.",
        "",
        "## C. Fixed Price by Deliverable",
        "",
        "| Deliverable Milestone | Payment % | Amount (USD) |",
        "| --- | --- | --- |",
        "| Approved Final Inception Report (Jul 28, 2025) | 20% | 3,000 |",
        "| Approved Workshop + Draft Evaluation Report (Sep 15, 2025) | 30% | 4,500 |",
        "| Approved Final Evaluation Report + Stand-alone Brief (Sep 30, 2025) | 50% | 7,500 |",
        "| Total | 100% | 15,000 |",
    ]

    annex_lines = [
        "# ANNEX TEMPLATES",
        "",
        "## Annex A. Evaluation Matrix (short template)",
        "",
        "| Evaluation Question | Indicator / Judgment Criteria | Data Source | Method | Respondents | Analysis Method |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if questions:
        for question in questions:
            annex_lines.append(f"| {question} | [Insert criteria] | [Insert source] | [Insert method] | [Insert respondents] | [Insert analysis method] |")
    else:
        annex_lines.append("| [Insert question] | [Insert criteria] | [Insert source] | [Insert method] | [Insert respondents] | [Insert analysis method] |")
    annex_lines.extend(
        [
            "",
            "## Annex B. Risk Register Template",
            "",
            "| Risk | Probability | Impact | Mitigation | Owner |",
            "| --- | --- | --- | --- | --- |",
            "| [Insert risk] | [L/M/H] | [L/M/H] | [Insert mitigation] | [Insert owner] |",
            "",
            "## Annex C. Bi-weekly Update Template",
            "",
            "Reporting period",
            "Activities completed",
            "Activities upcoming",
            "Risks/issues requiring action",
            "Support needed from KATCH/Winrock",
            "",
            "## Annex D. Report Structure (aligned to Appendix C)",
            "",
            "Cover, Acronyms, ToC",
            "Executive Summary (≤2 pp)",
            "Sections 1–5 per RFQ",
            "Required annexes (tools, indicator table, bibliography, ToR, etc.)",
            "PII exclusion statement",
        ]
    )

    ready_email = "\n".join(
        [
            f"Subject: KATCH FINAL ASSESSMENT - {rfq_title}",
            "Dear KATCH Procurement Team,",
            "Please find attached our Technical and Financial Proposals for RFQ-2025-001-KATCH-10019 (KATCH Final Assessment).",
            "Our submission is fully aligned with the scope of work, required methodology, deliverables, ethical standards, and timeline specified in the RFQ.",
            "Please let us know if any additional documents are required.",
            "Sincerely,",
            "[Name]",
            "[Title]",
            "[Organization]",
            "[Phone]",
            "[Email]",
            "",
        ]
    )

    base = "rfq_submission_kit"
    return {
        f"{base}/FILE 1 - TECHNICAL PROPOSAL ({rfq_title}).md": ("\n".join(technical_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 2 - FINANCIAL PROPOSAL ({rfq_title}).md": ("\n".join(financial_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 3 - ANNEX TEMPLATES.md": ("\n".join(annex_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 4 - READY EMAIL (EN).txt": ready_email.encode("utf-8"),
    }


def _evaluation_rfq_submission_kit_artifacts(*, donor_id: str, toc_draft: dict, export_contract: dict) -> dict[str, bytes]:
    contract = evaluate_export_contract(donor_id=donor_id, toc_payload=toc_draft)
    if str(contract.get("template_key") or "") != "evaluation_rfq":
        return {}

    normalized_toc = normalize_toc_for_export("evaluation_rfq", toc_draft)
    if str(normalized_toc.get("rfq_profile") or "").strip().lower() == KATCH_EVALUATION_RFQ_PROFILE:
        return _katch_submission_kit_artifacts(normalized_toc)
    rfq_title = _rfq_file_title(normalized_toc)
    organization_information = _clean_md_text(normalized_toc.get("organization_information"))
    evaluation_purpose = _clean_md_text(normalized_toc.get("evaluation_purpose"))
    background_context = _clean_md_text(normalized_toc.get("background_context"))
    technical_approach_summary = _clean_md_text(normalized_toc.get("technical_approach_summary"))
    methodology_overview = _clean_md_text(normalized_toc.get("methodology_overview"))
    sampling_plan = _clean_md_text(normalized_toc.get("sampling_plan"))
    level_of_effort_summary = _clean_md_text(normalized_toc.get("level_of_effort_summary"))
    technical_experience_summary = _clean_md_text(normalized_toc.get("technical_experience_summary"))
    financial_summary = _clean_md_text(normalized_toc.get("financial_summary"))
    payment_schedule_summary = _clean_md_text(normalized_toc.get("payment_schedule_summary"))
    questions = [str(item).strip() for item in (normalized_toc.get("evaluation_questions") or []) if str(item).strip()]
    methods = [item for item in (normalized_toc.get("methodology_components") or []) if isinstance(item, dict)]
    ethics = [str(item).strip() for item in (normalized_toc.get("ethical_considerations") or []) if str(item).strip()]
    risks = [str(item).strip() for item in (normalized_toc.get("assumptions_risks") or []) if str(item).strip()]
    deliverables = [item for item in (normalized_toc.get("deliverables") or []) if isinstance(item, dict)]
    schedule_rows = [item for item in (normalized_toc.get("deliverables_schedule_table") or []) if isinstance(item, dict)]
    key_personnel = [item for item in (normalized_toc.get("key_personnel") or []) if isinstance(item, dict)]
    team_roles = [item for item in (normalized_toc.get("team_composition") or []) if isinstance(item, dict)]
    cost_structure = [item for item in (normalized_toc.get("cost_structure") or []) if isinstance(item, dict)]
    pricing_assumptions = [
        str(item).strip() for item in (normalized_toc.get("pricing_assumptions") or []) if str(item).strip()
    ]
    question_matrix = [
        item for item in (normalized_toc.get("evaluation_questions_matrix") or []) if isinstance(item, dict)
    ]

    technical_lines = [
        f"# TECHNICAL PROPOSAL ({rfq_title})",
        "",
        "## 1. Organization Information",
        "",
        organization_information or "[Insert legal entity information, registration status, and authorized contact.]",
        "",
        "Annexes attached:",
        "- Business registration certificate",
        "- Latest audited financial statement",
        "",
        "## 2. Analysis and Proposed Approaches / Methodologies",
        "",
        "### 2.1 Understanding of the Assignment",
        "",
        evaluation_purpose
        or "Summative, learning-oriented evaluation to assess relevance, effectiveness, efficiency, sustainability, and outcomes.",
    ]
    if background_context:
        technical_lines.extend(["", background_context])
    technical_lines.extend(
        [
            "",
            "### 2.2 Evaluation Approach",
            "",
            technical_approach_summary or methodology_overview or "Theory-based, RBM-aligned mixed-method evaluation approach.",
            "",
            "### 2.3 Evaluation Questions",
            "",
        ]
    )
    if questions:
        technical_lines.extend([f"- {question}" for question in questions])
    else:
        technical_lines.append("- Refine evaluation questions at inception under the agreed RFQ criteria.")
    technical_lines.extend(["", "### 2.4 Data Collection Methods", ""])
    if methods:
        for idx, method in enumerate(methods, start=1):
            technical_lines.extend(
                [
                    f"{chr(64 + idx)}) {_clean_md_text(method.get('method')) or f'Method {idx}'}",
                    _clean_md_text(method.get("purpose")) or "Purpose to be refined during inception.",
                    "",
                    f"- Respondent group: {_clean_md_text(method.get('respondent_group')) or '-'}",
                    f"- Evidence source: {_clean_md_text(method.get('evidence_source')) or '-'}",
                    "",
                ]
            )
    else:
        technical_lines.append("- Desk review, KIIs, FGDs, survey, and outcome-oriented validation methods.")
    technical_lines.extend(["### 2.5 Sampling and Coverage", "", sampling_plan or "Sampling plan to be refined during inception."])
    software = [
        str(item).strip() for item in (normalized_toc.get("analytical_software") or []) if str(item).strip()
    ]
    technical_lines.extend(["", "### 2.6 Data Analysis", ""])
    if software:
        technical_lines.append(
            "Integrated analysis will combine qualitative coding, descriptive analysis, and triangulation using: "
            + ", ".join(software)
            + "."
        )
    else:
        technical_lines.append("Integrated analysis will combine qualitative coding, descriptive analysis, and triangulation.")
    technical_lines.extend(["", "### 2.7 Ethical Considerations and Safeguarding", ""])
    if ethics:
        technical_lines.extend([f"- {item}" for item in ethics])
    else:
        technical_lines.append("- Apply informed consent, confidentiality, and do-no-harm safeguards.")
    technical_lines.extend(["", "### 2.8 Potential Limitations and Mitigation", ""])
    if risks:
        technical_lines.extend([f"- {item}" for item in risks])
    else:
        technical_lines.append("- Potential limitations and mitigation measures to be refined at inception.")
    technical_lines.extend(["", "## 3. Work Plan", ""])
    if schedule_rows:
        technical_lines.append(
            _markdown_table(
                ["Deliverable", "Timeline", "Owner", "Dependencies", "Review Gate"],
                [
                    [
                        _clean_md_text(row.get("deliverable")),
                        _clean_md_text(row.get("due_window")),
                        _clean_md_text(row.get("owner")),
                        ", ".join(row.get("dependencies") or []) or "-",
                        _clean_md_text(row.get("review_gate")),
                    ]
                    for row in schedule_rows
                ],
            )
        )
    else:
        technical_lines.append("- Work plan and milestones to be confirmed in the inception package.")
    technical_lines.extend(["", "## 4. Proposed LOE", ""])
    if key_personnel:
        technical_lines.append(
            _markdown_table(
                ["Role", "Personnel", "Indicative LOE", "Qualifications"],
                [
                    [
                        _clean_md_text(row.get("role")),
                        _clean_md_text(row.get("name")),
                        _clean_md_text(row.get("level_of_effort")),
                        _clean_md_text(row.get("qualifications")),
                    ]
                    for row in key_personnel
                ],
            )
        )
    else:
        technical_lines.append(level_of_effort_summary or "Indicative LOE table to be completed during proposal finalization.")
    technical_lines.extend(["", "## 5. Technical Experience & Past Performance", ""])
    technical_lines.append(
        technical_experience_summary
        or "Insert 3-5 relevant final evaluations, mixed-method assessments, or systems-strengthening reviews."
    )
    technical_lines.extend(["", "## 6. Personnel and Team Composition", ""])
    if team_roles:
        technical_lines.extend(
            [
                f"- {_clean_md_text(row.get('role'))}: {_clean_md_text(row.get('responsibility')) or '-'}"
                for row in team_roles
            ]
        )
    elif key_personnel:
        technical_lines.extend(
            [
                f"- {_clean_md_text(row.get('role'))}: {_clean_md_text(row.get('qualifications')) or '-'}"
                for row in key_personnel
            ]
        )
    else:
        technical_lines.append("- Key personnel and delivery roles to be inserted.")
    technical_lines.extend(["", "## 7. Deliverables", ""])
    if deliverables:
        technical_lines.extend(
            [
                f"- {_clean_md_text(row.get('deliverable'))} | timing: {_clean_md_text(row.get('timing')) or '-'} | purpose: {_clean_md_text(row.get('purpose')) or '-'}"
                for row in deliverables
            ]
        )
    else:
        technical_lines.append("- Deliverable package to be finalized against the RFQ schedule.")

    financial_lines = [
        f"# FINANCIAL PROPOSAL ({rfq_title})",
        "",
        "Currency: USD",
        "Contract Type: Firm Fixed Price",
        "Total Price: [insert total fixed price]",
        "",
        "## A. Budget Table",
        "",
    ]
    if cost_structure:
        financial_lines.append(
            _markdown_table(
                ["Cost Category", "Basis", "Estimate", "Notes"],
                [
                    [
                        _clean_md_text(row.get("cost_bucket")),
                        _clean_md_text(row.get("basis")),
                        _clean_md_text(row.get("estimate")) or "[insert estimate]",
                        _clean_md_text(row.get("notes")),
                    ]
                    for row in cost_structure
                ],
            )
        )
    else:
        financial_lines.append(
            _markdown_table(
                ["Cost Category", "Basis", "Estimate", "Notes"],
                [["Professional fees", "Indicative LOE", "[insert estimate]", "-"]],
            )
        )
    financial_lines.extend(["", "## B. Budget Narrative", ""])
    financial_lines.append(
        financial_summary
        or "The budget is based on the proposed level of effort, field coordination requirements, data collection and processing needs, and reporting deliverables."
    )
    financial_lines.extend(["", "## C. Fixed Price by Deliverable", ""])
    if schedule_rows:
        financial_lines.append(
            _markdown_table(
                ["Deliverable Milestone", "Payment %", "Amount (USD)"],
                [
                    [
                        _clean_md_text(row.get("deliverable")),
                        "[insert %]",
                        "[insert amount]",
                    ]
                    for row in schedule_rows
                ],
            )
        )
    else:
        financial_lines.append(
            _markdown_table(
                ["Deliverable Milestone", "Payment %", "Amount (USD)"],
                [["Approved final deliverable package", "[insert %]", "[insert amount]"]],
            )
        )
    if payment_schedule_summary:
        financial_lines.extend(["", payment_schedule_summary])
    if pricing_assumptions:
        financial_lines.extend(["", "Pricing assumptions:"])
        financial_lines.extend([f"- {item}" for item in pricing_assumptions])

    annex_lines = [
        "# ANNEX TEMPLATES",
        "",
        "## Annex A. Evaluation Matrix (short template)",
        "",
    ]
    if question_matrix:
        annex_lines.append(
            _markdown_table(
                ["Evaluation Question", "Indicator / Judgment Criteria", "Data Source", "Method", "Respondents", "Analysis Method"],
                [
                    [
                        _clean_md_text(row.get("evaluation_question")),
                        "[insert criteria]",
                        ", ".join(row.get("evidence_sources") or []) or "[insert source]",
                        ", ".join(row.get("key_methods") or []) or "[insert method]",
                        "[insert respondents]",
                        _clean_md_text(row.get("reporting_use")) or "[insert analysis method]",
                    ]
                    for row in question_matrix
                ],
            )
        )
    else:
        annex_lines.append(
            _markdown_table(
                ["Evaluation Question", "Indicator / Judgment Criteria", "Data Source", "Method", "Respondents", "Analysis Method"],
                [["[insert question]", "[insert criteria]", "[insert source]", "[insert method]", "[insert respondents]", "[insert analysis]"]],
            )
        )
    annex_lines.extend(
        [
            "",
            "## Annex B. Risk Register Template",
            "",
            _markdown_table(
                ["Risk", "Probability", "Impact", "Mitigation", "Owner"],
                [["[insert risk]", "[L/M/H]", "[L/M/H]", "[insert mitigation]", "[insert owner]"]],
            ),
            "",
            "## Annex C. Bi-weekly Update Template",
            "",
            "- Reporting period",
            "- Activities completed",
            "- Activities upcoming",
            "- Risks/issues requiring action",
            "- Support needed from client / donor team",
            "",
            "## Annex D. Report Structure",
            "",
            "- Cover, Acronyms, ToC",
            "- Executive Summary",
            "- Main sections per RFQ",
            "- Required annexes (tools, indicator table, bibliography, ToR, etc.)",
            "- PII exclusion statement",
        ]
    )

    contact_name = "[Name]"
    contact_title = "[Title]"
    contact_org = "[Organization]"
    contact_phone = "[Phone]"
    contact_email = "[Email]"
    if organization_information:
        contact_org = "[Organization name from proposal cover]"
    ready_email = "\n".join(
        [
            f"Subject: KATCH FINAL ASSESSMENT - {rfq_title}",
            "",
            "Dear KATCH Procurement Team,",
            "",
            f"Please find attached our Technical and Financial Proposals for {rfq_title} (KATCH Final Assessment).",
            "",
            "Our submission is aligned with the scope of work, methodology, deliverables, ethical standards, and timeline specified in the RFQ.",
            "",
            "Please let us know if any additional documents are required.",
            "",
            "Sincerely,",
            contact_name,
            contact_title,
            contact_org,
            contact_phone,
            contact_email,
            "",
        ]
    )

    base = "rfq_submission_kit"
    return {
        f"{base}/FILE 1 - TECHNICAL PROPOSAL ({rfq_title}).md": ("\n".join(technical_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 2 - FINANCIAL PROPOSAL ({rfq_title}).md": ("\n".join(financial_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 3 - ANNEX TEMPLATES.md": ("\n".join(annex_lines) + "\n").encode("utf-8"),
        f"{base}/FILE 4 - READY EMAIL (EN).txt": ready_email.encode("utf-8"),
    }


def _app_module():
    from grantflow.api import app as api_app_module

    return api_app_module


@exports_router.get("/queue/dead-letter/export")
def export_dead_letter_queue(
    request: Request,
    limit: int = Query(default=500, ge=1, le=5000),
    format: str = Query(default="json"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    runner = _redis_queue_admin_runner(("list_dead_letters",))
    try:
        payload = runner.list_dead_letters(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_queue_dead_letter",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_dead_letter_queue_csv_text,
    )


@exports_router.get("/portfolio/metrics/export")
def export_portfolio_metrics(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    mel_risk_level: Optional[str] = None,
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_metrics_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        mel_risk_level=(mel_risk_level or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_metrics",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_metrics_csv_text,
    )


@exports_router.get("/portfolio/quality/export")
def export_portfolio_quality(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    finding_status: Optional[str] = None,
    finding_severity: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    mel_risk_level: Optional[str] = None,
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_quality_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        finding_status=(finding_status or None),
        finding_severity=(finding_severity or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        mel_risk_level=(mel_risk_level or None),
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_quality",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_quality_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/export")
def export_portfolio_review_workflow(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/sla/export")
def export_portfolio_review_workflow_sla(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_sla_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow_sla",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_sla_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/sla/hotspots/export")
def export_portfolio_review_workflow_sla_hotspots(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_sla_hotspots_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow_sla_hotspots",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_sla_hotspots_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/sla/hotspots/trends/export")
def export_portfolio_review_workflow_sla_hotspots_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_sla_hotspots_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow_sla_hotspots_trends",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_sla_hotspots_trends_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/trends/export")
def export_portfolio_review_workflow_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow_trends",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_trends_csv_text,
    )


@exports_router.get("/portfolio/review-workflow/sla/trends/export")
def export_portfolio_review_workflow_sla_trends(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    status: Optional[str] = None,
    hitl_enabled: Optional[bool] = Query(default=None),
    warning_level: Optional[str] = None,
    grounding_risk_level: Optional[str] = None,
    toc_text_risk_level: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    jobs = _filter_jobs_by_tenant(_list_jobs(), resolved_tenant_id)
    payload = public_portfolio_review_workflow_sla_trends_payload(
        jobs,
        donor_id=(donor_id or None),
        status=(status or None),
        hitl_enabled=hitl_enabled,
        warning_level=(warning_level or None),
        grounding_risk_level=(grounding_risk_level or None),
        toc_text_risk_level=(toc_text_risk_level or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )

    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_portfolio_review_workflow_sla_trends",
        donor_id=donor_id,
        status=status,
        hitl_enabled=hitl_enabled,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_portfolio_review_workflow_sla_trends_csv_text,
    )


@exports_router.get(
    "/status/{job_id}/export-payload",
    response_model=JobExportPayloadPublicResponse,
    response_model_exclude_none=True,
)
def get_status_export_payload(job_id: str, request: Request):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job_tenant_id = _job_tenant_id(job)
    donor = _job_donor_id(job)
    inventory_rows = _ingest_inventory(donor_id=donor or None, tenant_id=job_tenant_id)
    return public_job_export_payload(job_id, job, ingest_inventory_rows=inventory_rows)


@exports_router.get("/status/{job_id}/events/export")
def export_status_events(
    job_id: str,
    request: Request,
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    payload = public_job_events_payload(job_id, job)
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_job_events_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_job_events_csv_text,
    )


@exports_router.get("/status/{job_id}/hitl/history/export")
def export_status_hitl_history(
    job_id: str,
    request: Request,
    event_type: Optional[str] = Query(default=None),
    checkpoint_id: Optional[str] = Query(default=None),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    payload = _hitl_history_payload(
        job_id,
        job,
        event_type=(event_type or None),
        checkpoint_id=(checkpoint_id or None),
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_hitl_history_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_hitl_history_csv_text,
    )


@exports_router.get("/status/{job_id}/comments/export")
def export_status_comments(
    job_id: str,
    request: Request,
    section: Optional[str] = None,
    comment_status: Optional[str] = Query(default=None, alias="status"),
    version_id: Optional[str] = None,
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_comments_payload(
        job_id,
        job,
        section=section,
        comment_status=comment_status,
        version_id=version_id,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_comments_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=_job_comments_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/sla/hotspots/export")
def export_status_review_workflow_sla_hotspots(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_sla_hotspots_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_sla_hotspots_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_sla_hotspots_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/sla/hotspots/trends/export")
def export_status_review_workflow_sla_hotspots_trends(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    top_limit: int = Query(default=10, ge=1, le=200, alias="top_limit"),
    hotspot_kind: Optional[str] = Query(default=None, alias="hotspot_kind"),
    hotspot_severity: Optional[str] = Query(default=None, alias="hotspot_severity"),
    min_overdue_hours: Optional[float] = Query(default=None, ge=0.0, le=24 * 365, alias="min_overdue_hours"),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    hotspot_kind_filter = _validated_filter_token(
        hotspot_kind,
        allowed={"finding", "comment"},
        detail="Unsupported hotspot_kind filter",
    )
    hotspot_severity_filter = _validated_filter_token(
        hotspot_severity,
        allowed={"high", "medium", "low", "unknown"},
        detail="Unsupported hotspot_severity filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_sla_hotspots_trends_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
        top_limit=top_limit,
        hotspot_kind=hotspot_kind_filter,
        hotspot_severity=hotspot_severity_filter,
        min_overdue_hours=min_overdue_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_sla_hotspots_trends_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_sla_hotspots_trends_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/sla/export")
def export_status_review_workflow_sla(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_sla_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_sla_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_sla_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/sla/trends/export")
def export_status_review_workflow_sla_trends(
    job_id: str,
    request: Request,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_sla_trends_payload(
        job_id,
        job,
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_sla_trends_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_sla_trends_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/export")
def export_status_review_workflow(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_csv_text,
    )


@exports_router.get("/status/{job_id}/review/workflow/trends/export")
def export_status_review_workflow_trends(
    job_id: str,
    request: Request,
    event_type: Optional[str] = None,
    finding_id: Optional[str] = None,
    finding_code: Optional[str] = Query(default=None, alias="finding_code"),
    finding_section: Optional[str] = Query(default=None, alias="finding_section"),
    comment_status: Optional[str] = Query(default=None, alias="comment_status"),
    workflow_state: Optional[str] = Query(default=None, alias="workflow_state"),
    overdue_after_hours: int = Query(
        default=REVIEW_WORKFLOW_OVERDUE_DEFAULT_HOURS,
        ge=1,
        le=24 * 30,
        alias="overdue_after_hours",
    ),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    workflow_state_filter = str(workflow_state or "").strip().lower() or None
    if workflow_state_filter and workflow_state_filter not in REVIEW_WORKFLOW_STATE_FILTER_VALUES:
        raise HTTPException(status_code=400, detail="Unsupported workflow_state filter")
    finding_section_filter = _validated_filter_token(
        finding_section,
        allowed={"toc", "logframe", "general"},
        detail="Unsupported finding_section filter",
    )
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _ensure_job_tenant_read_access(request, job)
    job = _normalize_critic_fatal_flaws_for_job(job_id) or job
    job = _normalize_review_comments_for_job(job_id) or job
    payload = public_job_review_workflow_trends_payload(
        job_id,
        job,
        event_type=(event_type or None),
        finding_id=(finding_id or None),
        finding_code=(str(finding_code or "").strip() or None),
        finding_section=finding_section_filter,
        comment_status=(comment_status or None),
        workflow_state=workflow_state_filter,
        overdue_after_hours=overdue_after_hours,
    )
    return _portfolio_export_response(
        payload=payload,
        filename_prefix=f"grantflow_review_workflow_trends_{job_id}",
        donor_id=None,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_job_review_workflow_trends_csv_text,
    )


@exports_router.get("/ingest/inventory/export")
def export_ingest_inventory(
    request: Request,
    donor_id: Optional[str] = None,
    tenant_id: Optional[str] = Query(default=None),
    format: str = Query(default="csv"),
    gzip_enabled: bool = Query(default=False, alias="gzip"),
):
    require_api_key_if_configured(request, for_read=True)
    resolved_tenant_id = _resolve_tenant_id(request, explicit_tenant=tenant_id, require_if_enabled=True)
    rows = _ingest_inventory(donor_id=donor_id, tenant_id=resolved_tenant_id)
    payload = public_ingest_inventory_payload(rows, donor_id=(donor_id or None), tenant_id=resolved_tenant_id)
    return _portfolio_export_response(
        payload=payload,
        filename_prefix="grantflow_ingest_inventory",
        donor_id=donor_id,
        status=None,
        hitl_enabled=None,
        export_format=format,
        gzip_enabled=gzip_enabled,
        csv_renderer=public_ingest_inventory_csv_text,
    )


@exports_router.post("/export")
def export_artifacts(req: ExportRequest, request: Request):
    require_api_key_if_configured(request)
    grounding_gate = _extract_export_grounding_gate(req)
    runtime_grounded_gate = _extract_export_runtime_grounded_quality_gate(req)
    if (
        _configured_export_require_grounded_gate_pass()
        and not req.allow_unsafe_export
        and (bool(runtime_grounded_gate.get("blocking")) or runtime_grounded_gate.get("passed") is False)
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "runtime_grounded_quality_gate_block",
                "message": (
                    "Export blocked by runtime grounded quality gate pass policy. "
                    "Set allow_unsafe_export=true to override."
                ),
                "grounded_gate": runtime_grounded_gate,
            },
        )
    if (
        not req.allow_unsafe_export
        and bool(grounding_gate.get("blocking"))
        and str(grounding_gate.get("mode") or "").lower() == "strict"
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "grounding_gate_strict_block",
                "message": "Export blocked by strict grounding gate. Set allow_unsafe_export=true to override.",
                "grounding_gate": grounding_gate,
            },
        )
    toc_draft, logframe_draft, donor_id, citations, critic_findings, review_comments, quality_summary = (
        _resolve_export_inputs(req)
    )
    fmt = (req.format or "").lower()
    export_contract_gate = _evaluate_export_contract_gate(donor_id=donor_id, toc_draft=toc_draft)
    if (
        req.production_export
        and not req.allow_unsafe_export
        and fmt == "docx"
        and bool(export_contract_gate.get("blocking"))
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "export_contract_policy_block",
                "message": (
                    "Export blocked by strict export contract policy "
                    "(missing required donor sections/sheets). "
                    "Set allow_unsafe_export=true to override, or use production_export=false."
                ),
                "export_contract_gate": export_contract_gate,
            },
        )
    export_grounding_policy = _evaluate_export_grounding_policy(citations)
    if not req.allow_unsafe_export and bool(export_grounding_policy.get("blocking")):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "export_grounding_policy_block",
                "message": (
                    "Export blocked by strict export grounding policy "
                    "(architect claim support below configured threshold). "
                    "Set allow_unsafe_export=true to override."
                ),
                "export_grounding_policy": export_grounding_policy,
            },
        )
    try:
        docx_bytes: Optional[bytes] = None
        xlsx_bytes: Optional[bytes] = None

        if fmt in {"docx", "both"}:
            docx_bytes = _app_module().build_docx_from_toc(
                toc_draft,
                donor_id,
                logframe_draft=logframe_draft,
                citations=citations,
                critic_findings=critic_findings,
                review_comments=review_comments,
                quality_summary=quality_summary,
            )

        if fmt in {"xlsx", "both"}:
            xlsx_bytes = _app_module().build_xlsx_from_logframe(
                logframe_draft,
                donor_id,
                toc_draft=toc_draft,
                citations=citations,
                critic_findings=critic_findings,
                review_comments=review_comments,
                quality_summary=quality_summary,
            )

        if xlsx_bytes is not None:
            workbook_sheetnames, workbook_primary_sheet_headers = _xlsx_contract_validation_context(
                xlsx_bytes,
                donor_id=donor_id,
            )
            export_contract_gate = _evaluate_export_contract_gate(
                donor_id=donor_id,
                toc_draft=toc_draft,
                workbook_sheetnames=workbook_sheetnames,
                workbook_primary_sheet_headers=workbook_primary_sheet_headers,
            )
            if req.production_export and not req.allow_unsafe_export and bool(export_contract_gate.get("blocking")):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "export_contract_policy_block",
                        "message": (
                            "Export blocked by strict export contract policy "
                            "(missing required donor sections/sheets). "
                            "Set allow_unsafe_export=true to override, or use production_export=false."
                        ),
                        "export_contract_gate": export_contract_gate,
                    },
                )

        export_headers = {
            "X-GrantFlow-Export-Contract-Mode": str(export_contract_gate.get("mode") or ""),
            "X-GrantFlow-Export-Contract-Status": str(export_contract_gate.get("status") or ""),
            "X-GrantFlow-Export-Contract-Summary": str(export_contract_gate.get("summary") or ""),
        }

        if fmt == "docx" and docx_bytes is not None:
            headers = {
                "Content-Disposition": "attachment; filename=proposal.docx",
                **export_headers,
            }
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers=headers,
            )

        if fmt == "xlsx" and xlsx_bytes is not None:
            headers = {
                "Content-Disposition": "attachment; filename=mel.xlsx",
                **export_headers,
            }
            return StreamingResponse(
                io.BytesIO(xlsx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers=headers,
            )

        if fmt == "both" and docx_bytes is not None and xlsx_bytes is not None:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("proposal.docx", docx_bytes)
                archive.writestr("mel.xlsx", xlsx_bytes)
                for filename, content in _evaluation_rfq_annex_pack_artifacts(
                    donor_id=donor_id,
                    toc_draft=toc_draft,
                    export_contract=export_contract_gate,
                ).items():
                    archive.writestr(filename, content)
                for filename, content in _evaluation_rfq_submission_kit_artifacts(
                    donor_id=donor_id,
                    toc_draft=toc_draft,
                    export_contract=export_contract_gate,
                ).items():
                    archive.writestr(filename, content)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/zip",
                headers={
                    "Content-Disposition": "attachment; filename=grantflow_export.zip",
                    **export_headers,
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="Unsupported format")
