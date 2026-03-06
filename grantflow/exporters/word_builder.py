# grantflow/exporters/word_builder.py

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from grantflow.exporters.donor_contracts import evaluate_export_contract
from grantflow.exporters.template_profile import build_export_template_profile, normalize_export_template_key
from grantflow.exporters.toc_normalization import normalize_toc_for_export, unwrap_toc_payload


def _normalized_indicator_rows(logframe_draft: Optional[Dict[str, Any]]) -> list[Dict[str, Any]]:
    if not isinstance(logframe_draft, dict):
        return []
    raw = logframe_draft.get("indicators")
    return [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []


def _indicator_focus_rows(
    indicators: list[Dict[str, Any]],
    *,
    result_level: Optional[str] = None,
    limit: int = 2,
) -> list[Dict[str, Any]]:
    rows = indicators
    if result_level:
        token = str(result_level).strip().lower()
        rows = [row for row in indicators if str(row.get("result_level") or "").strip().lower() == token]
    return rows[: max(0, limit)]


def _add_indicator_focus_block(
    doc: Document,
    *,
    indicators: list[Dict[str, Any]],
    label: str = "Monitoring focus",
) -> None:
    focus_rows = [row for row in indicators if isinstance(row, dict)]
    if not focus_rows:
        return
    doc.add_paragraph(f"{label}:", style="List Bullet")
    for row in focus_rows:
        name = str(row.get("name") or "").strip() or str(row.get("indicator_id") or "Indicator")
        mov = str(row.get("means_of_verification") or "").strip()
        owner = str(row.get("owner") or "").strip()
        line = name
        if mov:
            line += f" | Means of verification: {mov}"
        if owner:
            line += f" | Owner: {owner}"
        doc.add_paragraph(line, style="List Bullet")


def _review_readiness_rows(
    *,
    quality_summary: dict[str, Any],
    citations: list[Dict[str, Any]],
    critic_findings: list[Dict[str, Any]],
    review_comments: list[Dict[str, Any]],
) -> list[tuple[str, Any]]:
    open_findings = [
        item
        for item in critic_findings
        if isinstance(item, dict) and str(item.get("status") or "open").strip().lower() not in {"resolved", "closed"}
    ]
    high_findings = [
        item
        for item in open_findings
        if str(item.get("severity") or "").strip().lower() in {"high", "critical", "fatal"}
    ]
    open_comments = [
        item
        for item in review_comments
        if isinstance(item, dict) and str(item.get("status") or "open").strip().lower() not in {"resolved", "closed"}
    ]
    low_confidence = [
        item
        for item in citations
        if isinstance(item, dict) and str(item.get("citation_type") or "").strip().lower() == "rag_low_confidence"
    ]
    fallback = [
        item
        for item in citations
        if isinstance(item, dict)
        and str(item.get("citation_type") or "").strip().lower() in {"fallback_namespace", "strategy_reference"}
    ]
    rows = [
        ("Needs revision", quality_summary.get("needs_revision")),
        ("Open critic findings", len(open_findings)),
        ("High-severity open findings", len(high_findings)),
        ("Open review comments", len(open_comments)),
        ("Low-confidence citations", len(low_confidence)),
        ("Fallback/strategy citations", len(fallback)),
    ]
    return [(label, value) for label, value in rows if value is not None and value != ""]


def _citation_summary_line(citation: Dict[str, Any]) -> str:
    stage = citation.get("stage", "")
    ctype = citation.get("citation_type", "")
    used_for = citation.get("used_for", "")
    label = citation.get("label") or citation.get("source") or citation.get("namespace") or ""
    page = citation.get("page")
    chunk = citation.get("chunk")
    confidence = citation.get("citation_confidence")
    statement_path = citation.get("statement_path")
    result_level = citation.get("result_level")

    parts = []
    if stage:
        parts.append(f"[{stage}]")
    if ctype:
        parts.append(str(ctype))
    if used_for:
        parts.append(f"for {used_for}")
    if label:
        parts.append(f"- {label}")
    if confidence is not None:
        try:
            parts.append(f"(conf {float(confidence):.2f})")
        except (TypeError, ValueError):
            parts.append(f"(conf {confidence})")
    if result_level:
        parts.append(f"(level {result_level})")
    if statement_path:
        parts.append(f"(path {statement_path})")
    if page is not None:
        parts.append(f"(p.{page})")
    if chunk is not None:
        parts.append(f"(chunk {chunk})")
    return " ".join(parts).strip()


def _add_citation_traceability_section(doc: Document, citations: list[Dict[str, Any]]) -> None:
    if not citations:
        return

    doc.add_heading("Citation Traceability", level=1)
    doc.add_paragraph(
        "Structured citation records collected during drafting (strategy references and/or RAG retrieval results)."
    )
    for citation in citations:
        doc.add_paragraph(_citation_summary_line(citation), style="List Bullet")
        excerpt = (citation.get("excerpt") or "").strip()
        if excerpt:
            p = doc.add_paragraph()
            p.add_run(f"Excerpt: {excerpt[:240]}").italic = True


def _add_critic_findings_section(doc: Document, critic_findings: list[Dict[str, Any]]) -> None:
    if not critic_findings:
        return

    doc.add_heading("Critic Findings", level=1)
    doc.add_paragraph("Rule-based and/or LLM critic findings captured during review.")
    for finding in critic_findings:
        status = finding.get("status") or "open"
        severity = finding.get("severity") or "unknown"
        code = finding.get("code") or "FINDING"
        section = finding.get("section") or "general"
        title = f"[{status}] [{severity}] {section} · {code}"
        doc.add_paragraph(title, style="List Bullet")
        message = str(finding.get("message") or "").strip()
        if message:
            doc.add_paragraph(message)
        fix_hint = str(finding.get("fix_hint") or "").strip()
        if fix_hint:
            p = doc.add_paragraph()
            p.add_run(f"Fix hint: {fix_hint}").italic = True
        finding_id = finding.get("id") or finding.get("finding_id")
        meta_bits: list[str] = []
        if finding.get("version_id"):
            meta_bits.append(f"version={finding.get('version_id')}")
        if finding_id:
            meta_bits.append(f"finding_id={finding_id}")
        if finding.get("source"):
            meta_bits.append(f"source={finding.get('source')}")
        if meta_bits:
            doc.add_paragraph(" · ".join(meta_bits))


def _add_review_comments_section(doc: Document, review_comments: list[Dict[str, Any]]) -> None:
    if not review_comments:
        return

    doc.add_heading("Review Comments", level=1)
    doc.add_paragraph("Reviewer notes and resolution workflow comments linked to draft versions/findings.")
    for comment in review_comments:
        status = comment.get("status") or "open"
        section = comment.get("section") or "general"
        author = comment.get("author") or "reviewer"
        title = f"[{status}] {section} · {author}"
        doc.add_paragraph(title, style="List Bullet")
        message = str(comment.get("message") or "").strip()
        if message:
            doc.add_paragraph(message)
        meta_bits: list[str] = []
        if comment.get("version_id"):
            meta_bits.append(f"version={comment.get('version_id')}")
        if comment.get("linked_finding_id"):
            meta_bits.append(f"linked_finding_id={comment.get('linked_finding_id')}")
        if comment.get("ts"):
            meta_bits.append(str(comment.get("ts")))
        if meta_bits:
            doc.add_paragraph(" · ".join(meta_bits))


def _add_quality_summary_section(doc: Document, quality_summary: dict[str, Any]) -> None:
    if not quality_summary:
        return

    rows = [
        ("Quality score", quality_summary.get("quality_score")),
        ("Critic score", quality_summary.get("critic_score")),
        ("Needs revision", quality_summary.get("needs_revision")),
        ("Critic engine", quality_summary.get("engine")),
        ("Rule score", quality_summary.get("rule_score")),
        ("LLM score", quality_summary.get("llm_score")),
        ("Fatal flaw count", quality_summary.get("fatal_flaw_count")),
        ("Citation count", quality_summary.get("citation_count")),
    ]
    present_rows = [(label, value) for label, value in rows if value is not None and value != ""]
    if not present_rows:
        return

    doc.add_heading("Quality Summary", level=1)
    doc.add_paragraph("Snapshot of current draft quality, critic status, and citation volume at export time.")
    for label, value in present_rows:
        doc.add_paragraph(f"{label}: {value}", style="List Bullet")


def _add_review_readiness_section(
    doc: Document,
    *,
    quality_summary: dict[str, Any],
    citations: list[Dict[str, Any]],
    critic_findings: list[Dict[str, Any]],
    review_comments: list[Dict[str, Any]],
) -> None:
    rows = _review_readiness_rows(
        quality_summary=quality_summary,
        citations=citations,
        critic_findings=critic_findings,
        review_comments=review_comments,
    )
    if not rows:
        return

    doc.add_heading("Review Readiness", level=1)
    doc.add_paragraph("Compact reviewer snapshot for triage before sign-off or export handoff.")
    for label, value in rows:
        doc.add_paragraph(f"{label}: {value}", style="List Bullet")


def _toc_root(toc_draft: Dict[str, Any], donor_id: str | None = None) -> Dict[str, Any]:
    if not donor_id:
        return unwrap_toc_payload(toc_draft)
    donor_key = normalize_export_template_key(donor_id)
    return normalize_toc_for_export(donor_key, unwrap_toc_payload(toc_draft))


def _render_usaid_toc(doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    impact_focus = _indicator_focus_rows(indicators, result_level="impact", limit=1)
    doc.add_heading("USAID Results Framework", level=1)
    goal = str(toc.get("project_goal") or "").strip()
    if goal:
        doc.add_heading("Project Goal", level=2)
        doc.add_paragraph(goal)
        _add_indicator_focus_block(doc, indicators=impact_focus, label="Suggested learning focus")

    do_list = toc.get("development_objectives")
    if isinstance(do_list, list) and do_list:
        doc.add_heading("Development Objectives", level=2)
        for do in do_list:
            if not isinstance(do, dict):
                continue
            do_id = str(do.get("do_id") or "").strip()
            do_title = str(do.get("description") or "").strip()
            doc.add_heading(f"{do_id or 'DO'} — {do_title or 'Development Objective'}", level=3)
            _add_indicator_focus_block(doc, indicators=outcome_focus, label="Suggested performance monitoring focus")
            ir_list = do.get("intermediate_results")
            if not isinstance(ir_list, list):
                continue
            for ir in ir_list:
                if not isinstance(ir, dict):
                    continue
                ir_id = str(ir.get("ir_id") or "").strip()
                ir_desc = str(ir.get("description") or "").strip()
                doc.add_paragraph(f"IR: {ir_id or '-'} — {ir_desc or '-'}", style="List Bullet")
                outputs = ir.get("outputs")
                if not isinstance(outputs, list):
                    continue
                for out in outputs:
                    if not isinstance(out, dict):
                        continue
                    output_id = str(out.get("output_id") or "").strip()
                    output_desc = str(out.get("description") or "").strip()
                    doc.add_paragraph(f"Output: {output_id or '-'} — {output_desc or '-'}", style="List Bullet")
                    indicators = out.get("indicators")
                    if not isinstance(indicators, list):
                        continue
                    for indicator in indicators:
                        if not isinstance(indicator, dict):
                            continue
                        code = str(indicator.get("indicator_code") or "").strip()
                        name = str(indicator.get("name") or "").strip()
                        target = str(indicator.get("target") or "").strip()
                        citation = str(indicator.get("citation") or "").strip()
                        line = f"Indicator: {code or '-'} — {name or '-'}"
                        if target:
                            line += f" | Target: {target}"
                        if citation:
                            line += f" | Citation: {citation}"
                        doc.add_paragraph(line, style="List Bullet")

    assumptions = toc.get("critical_assumptions")
    if isinstance(assumptions, list) and assumptions:
        doc.add_heading("Critical Assumptions", level=2)
        for assumption in assumptions:
            doc.add_paragraph(str(assumption), style="List Bullet")


def _render_eu_toc(doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    output_focus = _indicator_focus_rows(indicators, result_level="output", limit=2)
    doc.add_heading("EU Intervention Logic", level=1)
    overall = toc.get("overall_objective")
    rendered = False
    if isinstance(overall, dict):
        objective_id = str(overall.get("objective_id") or "").strip()
        title = str(overall.get("title") or "").strip()
        rationale = str(overall.get("rationale") or "").strip()
        doc.add_heading("Overall Objective", level=2)
        if objective_id or title:
            doc.add_paragraph(f"{objective_id or 'Objective'} — {title or '-'}")
        if rationale:
            doc.add_paragraph(rationale)
        _add_indicator_focus_block(doc, indicators=outcome_focus, label="Suggested monitoring focus")
        rendered = True

    specific_objectives = toc.get("specific_objectives")
    if isinstance(specific_objectives, list) and specific_objectives:
        doc.add_heading("Specific Objectives", level=2)
        for row in specific_objectives:
            if not isinstance(row, dict):
                continue
            objective_id = str(row.get("objective_id") or "").strip()
            title = str(row.get("title") or "").strip()
            rationale = str(row.get("rationale") or "").strip()
            doc.add_paragraph(f"{objective_id or 'SO'} — {title or '-'}", style="List Bullet")
            if rationale:
                doc.add_paragraph(rationale)
            _add_indicator_focus_block(doc, indicators=outcome_focus[:1], label="Suggested verification focus")
        rendered = True

    expected_outcomes = toc.get("expected_outcomes")
    if isinstance(expected_outcomes, list) and expected_outcomes:
        doc.add_heading("Expected Outcomes", level=2)
        for row in expected_outcomes:
            if not isinstance(row, dict):
                continue
            outcome_id = str(row.get("outcome_id") or "").strip()
            title = str(row.get("title") or "").strip()
            expected_change = str(row.get("expected_change") or "").strip()
            doc.add_paragraph(f"{outcome_id or 'Outcome'} — {title or '-'}", style="List Bullet")
            if expected_change:
                doc.add_paragraph(expected_change)
            _add_indicator_focus_block(
                doc, indicators=output_focus[:1] or outcome_focus[:1], label="Suggested delivery focus"
            )
        rendered = True

    assumptions = toc.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        doc.add_heading("Assumptions", level=2)
        for assumption in assumptions:
            doc.add_paragraph(str(assumption), style="List Bullet")
        rendered = True

    risks = toc.get("risks")
    if isinstance(risks, list) and risks:
        doc.add_heading("Risks", level=2)
        for risk in risks:
            doc.add_paragraph(str(risk), style="List Bullet")
        rendered = True

    if not rendered:
        doc.add_paragraph("Overall objective is not provided in EU schema draft.")


def _render_worldbank_toc(
    doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None
) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    impact_focus = _indicator_focus_rows(indicators, result_level="impact", limit=1)
    doc.add_heading("World Bank Results Framework", level=1)
    rendered = False
    pdo = str(toc.get("project_development_objective") or "").strip()
    if pdo:
        doc.add_heading("Project Development Objective (PDO)", level=2)
        doc.add_paragraph(pdo)
        _add_indicator_focus_block(
            doc, indicators=impact_focus or outcome_focus[:1], label="Suggested PDO monitoring focus"
        )
        rendered = True

    objectives = toc.get("objectives")
    if isinstance(objectives, list) and objectives:
        doc.add_heading("Objectives", level=2)
        for obj in objectives:
            if not isinstance(obj, dict):
                continue
            objective_id = str(obj.get("objective_id") or "").strip()
            title = str(obj.get("title") or "").strip()
            description = str(obj.get("description") or "").strip()
            doc.add_heading(f"{objective_id or 'Objective'} — {title or '-'}", level=3)
            _add_indicator_focus_block(
                doc,
                indicators=outcome_focus[:1] or impact_focus,
                label="Suggested results monitoring focus",
            )
            if description:
                doc.add_paragraph(description)
        rendered = True

    results_chain = toc.get("results_chain")
    if isinstance(results_chain, list) and results_chain:
        doc.add_heading("Results Chain", level=2)
        for row in results_chain:
            if not isinstance(row, dict):
                continue
            result_id = str(row.get("result_id") or "").strip()
            title = str(row.get("title") or "").strip()
            description = str(row.get("description") or "").strip()
            indicator_focus = str(row.get("indicator_focus") or "").strip()
            doc.add_paragraph(f"{result_id or 'Result'} — {title or '-'}", style="List Bullet")
            if description:
                doc.add_paragraph(description)
            if indicator_focus:
                p = doc.add_paragraph()
                p.add_run(f"Indicator focus: {indicator_focus}").italic = True
            _add_indicator_focus_block(
                doc,
                indicators=outcome_focus[:1] or impact_focus,
                label="Suggested verification focus",
            )
        rendered = True

    assumptions = toc.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        doc.add_heading("Assumptions", level=2)
        for assumption in assumptions:
            doc.add_paragraph(str(assumption), style="List Bullet")
        rendered = True

    risks = toc.get("risks")
    if isinstance(risks, list) and risks:
        doc.add_heading("Risks", level=2)
        for risk in risks:
            doc.add_paragraph(str(risk), style="List Bullet")
        rendered = True

    if not rendered:
        doc.add_paragraph("No World Bank objectives found in draft.")


def _render_giz_toc(doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    output_focus = _indicator_focus_rows(indicators, result_level="output", limit=2)
    doc.add_heading("GIZ Results & Sustainability Logic", level=1)
    rendered = False

    programme_objective = str(toc.get("programme_objective") or "").strip()
    if programme_objective:
        doc.add_heading("Programme Objective", level=2)
        doc.add_paragraph(programme_objective)
        _add_indicator_focus_block(
            doc,
            indicators=outcome_focus[:1],
            label="Suggested implementation monitoring focus",
        )
        rendered = True

    outputs = toc.get("outputs")
    if isinstance(outputs, list) and outputs:
        doc.add_heading("Outputs", level=2)
        for output in outputs:
            doc.add_paragraph(str(output), style="List Bullet")
        _add_indicator_focus_block(
            doc,
            indicators=output_focus[:1] or outcome_focus[:1],
            label="Suggested delivery verification focus",
        )
        rendered = True

    outcomes = toc.get("outcomes")
    if isinstance(outcomes, list) and outcomes:
        doc.add_heading("Outcomes", level=2)
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            title = str(outcome.get("title") or "").strip()
            description = str(outcome.get("description") or "").strip()
            partner_role = str(outcome.get("partner_role") or "").strip()
            doc.add_paragraph(title or "Outcome", style="List Bullet")
            if description:
                doc.add_paragraph(description)
            if partner_role:
                p = doc.add_paragraph()
                p.add_run(f"Partner role: {partner_role}").italic = True
            _add_indicator_focus_block(
                doc,
                indicators=outcome_focus[:1],
                label="Suggested sustainability monitoring focus",
            )
        rendered = True

    sustainability_factors = toc.get("sustainability_factors")
    if isinstance(sustainability_factors, list) and sustainability_factors:
        doc.add_heading("Sustainability Factors", level=2)
        for factor in sustainability_factors:
            doc.add_paragraph(str(factor), style="List Bullet")
        rendered = True

    assumptions_risks = toc.get("assumptions_risks")
    if isinstance(assumptions_risks, list) and assumptions_risks:
        doc.add_heading("Assumptions & Risks", level=2)
        for item in assumptions_risks:
            doc.add_paragraph(str(item), style="List Bullet")
        rendered = True

    if not rendered:
        doc.add_paragraph("No GIZ-specific ToC structure found in draft.")


def _render_un_agencies_toc(
    doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None
) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    impact_focus = _indicator_focus_rows(indicators, result_level="impact", limit=1)
    doc.add_heading("UN Agency Program Logic", level=1)

    brief = str(toc.get("brief") or "").strip()
    if brief:
        doc.add_heading("Overview", level=2)
        doc.add_paragraph(brief)
        _add_indicator_focus_block(
            doc,
            indicators=impact_focus or outcome_focus[:1],
            label="Suggested results focus",
        )

    objectives = toc.get("objectives")
    if isinstance(objectives, list) and objectives:
        doc.add_heading("Development Objectives", level=2)
        for row in objectives:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "Untitled").strip()
            description = str(row.get("description") or "").strip()
            doc.add_heading(title, level=3)
            if description:
                doc.add_paragraph(description)
            _add_indicator_focus_block(
                doc,
                indicators=outcome_focus[:1] or impact_focus,
                label="Suggested monitoring focus",
            )
            citation = str(row.get("citation") or "").strip()
            if citation:
                p = doc.add_paragraph()
                p.add_run(f"Citation: {citation}").italic = True

    outcomes = toc.get("outcomes")
    if isinstance(outcomes, list) and outcomes:
        doc.add_heading("Expected Outcomes", level=2)
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or row.get("name") or "Outcome").strip()
            description = str(row.get("description") or row.get("expected_change") or "").strip()
            doc.add_paragraph(title, style="List Bullet")
            if description:
                doc.add_paragraph(description)

    toc_indicators = toc.get("indicators")
    if isinstance(toc_indicators, list) and toc_indicators:
        doc.add_heading("Key Indicators", level=2)
        for ind in toc_indicators:
            if not isinstance(ind, dict):
                continue
            doc.add_paragraph(f"• {ind.get('name', 'Unknown')}", style="List Bullet")
            justification = str(ind.get("justification") or "").strip()
            if justification:
                doc.add_paragraph(f"  Justification: {justification}", style="Intense Quote")


def _render_state_department_toc(
    doc: Document, toc: Dict[str, Any], *, logframe_draft: Optional[Dict[str, Any]] = None
) -> None:
    indicators = _normalized_indicator_rows(logframe_draft)
    outcome_focus = _indicator_focus_rows(indicators, result_level="outcome", limit=2)
    impact_focus = _indicator_focus_rows(indicators, result_level="impact", limit=1)
    doc.add_heading("U.S. Department of State Program Logic", level=1)
    rendered = False

    strategic_context = str(toc.get("strategic_context") or "").strip()
    if strategic_context:
        doc.add_heading("Strategic Context", level=2)
        doc.add_paragraph(strategic_context)
        rendered = True

    program_goal = str(toc.get("program_goal") or "").strip()
    if program_goal:
        doc.add_heading("Program Goal", level=2)
        doc.add_paragraph(program_goal)
        _add_indicator_focus_block(
            doc,
            indicators=impact_focus or outcome_focus[:1],
            label="Suggested strategic monitoring focus",
        )
        rendered = True

    objectives = toc.get("objectives")
    if isinstance(objectives, list) and objectives:
        doc.add_heading("Objectives", level=2)
        for row in objectives:
            if not isinstance(row, dict):
                continue
            objective = str(row.get("objective") or "").strip()
            line_of_effort = str(row.get("line_of_effort") or "").strip()
            expected_change = str(row.get("expected_change") or "").strip()
            title = objective or "Objective"
            if line_of_effort:
                title += f" ({line_of_effort})"
            doc.add_paragraph(title, style="List Bullet")
            _add_indicator_focus_block(
                doc,
                indicators=outcome_focus[:1] or impact_focus,
                label="Suggested delivery monitoring focus",
            )
            if expected_change:
                doc.add_paragraph(expected_change)
        rendered = True

    stakeholder_map = toc.get("stakeholder_map")
    if isinstance(stakeholder_map, list) and stakeholder_map:
        doc.add_heading("Stakeholder Map", level=2)
        for stakeholder in stakeholder_map:
            doc.add_paragraph(str(stakeholder), style="List Bullet")
        rendered = True

    risk_mitigation = toc.get("risk_mitigation")
    if isinstance(risk_mitigation, list) and risk_mitigation:
        doc.add_heading("Risk Mitigation", level=2)
        for risk in risk_mitigation:
            doc.add_paragraph(str(risk), style="List Bullet")
        rendered = True

    if not rendered:
        doc.add_paragraph("No State Department-specific ToC structure found in draft.")


def _render_generic_toc(doc: Document, toc: Dict[str, Any]) -> None:
    if "brief" in toc:
        doc.add_heading("Overview", level=1)
        doc.add_paragraph(str(toc.get("brief") or ""))

    if "objectives" in toc and isinstance(toc.get("objectives"), list):
        doc.add_heading("Development Objectives", level=1)
        for obj in toc["objectives"]:
            if not isinstance(obj, dict):
                continue
            doc.add_heading(str(obj.get("title") or "Untitled"), level=2)
            doc.add_paragraph(str(obj.get("description") or ""))
            citation = str(obj.get("citation") or "").strip()
            if citation:
                p = doc.add_paragraph()
                p.add_run(f"Citation: {citation}").italic = True

    if "indicators" in toc and isinstance(toc.get("indicators"), list):
        doc.add_heading("Key Indicators", level=1)
        for ind in toc["indicators"]:
            if not isinstance(ind, dict):
                continue
            doc.add_paragraph(f"• {ind.get('name', 'Unknown')}", style="List Bullet")
            if "justification" in ind:
                doc.add_paragraph(f"  Justification: {ind['justification']}", style="Intense Quote")


def _add_mel_indicator_summary_section(doc: Document, logframe_draft: Optional[Dict[str, Any]]) -> None:
    if not isinstance(logframe_draft, dict):
        return
    indicators = logframe_draft.get("indicators")
    if not isinstance(indicators, list) or not indicators:
        return

    doc.add_heading("MEL Indicator Summary", level=1)
    for indicator in indicators:
        if not isinstance(indicator, dict):
            continue
        indicator_id = str(indicator.get("indicator_id") or "").strip()
        name = str(indicator.get("name") or "").strip() or "Untitled indicator"
        title = f"{indicator_id} — {name}" if indicator_id else name
        doc.add_paragraph(title, style="List Bullet")

        result_level = str(indicator.get("result_level") or "").strip()
        baseline = str(indicator.get("baseline") or "").strip()
        target = str(indicator.get("target") or "").strip()
        frequency = str(indicator.get("frequency") or "").strip()
        formula = str(indicator.get("formula") or "").strip()
        definition = str(indicator.get("definition") or "").strip()
        data_source = str(indicator.get("data_source") or "").strip()
        means_of_verification = str(indicator.get("means_of_verification") or "").strip()
        owner = str(indicator.get("owner") or "").strip()
        citation = str(indicator.get("citation") or "").strip()
        justification = str(indicator.get("justification") or "").strip()
        disaggregation_raw = indicator.get("disaggregation")
        disaggregation = ""
        if isinstance(disaggregation_raw, list):
            disaggregation = ", ".join(str(item).strip() for item in disaggregation_raw if str(item).strip())
        elif isinstance(disaggregation_raw, str):
            disaggregation = disaggregation_raw.strip()

        details: list[str] = []
        if result_level:
            details.append(f"Result level: {result_level}")
        if baseline or target:
            details.append(f"Baseline/Target: {baseline or '-'} -> {target or '-'}")
        if frequency:
            details.append(f"Frequency: {frequency}")
        if formula:
            details.append(f"Formula: {formula}")
        if definition:
            details.append(f"Definition: {definition}")
        if data_source:
            details.append(f"Data source: {data_source}")
        if means_of_verification:
            details.append(f"Means of verification: {means_of_verification}")
        if owner:
            details.append(f"Owner: {owner}")
        if disaggregation:
            details.append(f"Disaggregation: {disaggregation}")
        if citation:
            details.append(f"Citation: {citation}")
        if justification:
            details.append(f"Justification: {justification}")
        if details:
            doc.add_paragraph(" | ".join(details))


def _add_template_profile_section(doc: Document, profile: Dict[str, Any]) -> None:
    doc.add_heading("Template Profile", level=1)
    doc.add_paragraph(f"Template: {profile.get('template_display_name')} ({profile.get('template_key')})")
    doc.add_paragraph(f"Coverage rate: {float(profile.get('coverage_rate') or 0.0):.0%}")

    raw_required = profile.get("required_sections")
    required = list(raw_required) if isinstance(raw_required, list) else []
    raw_present = profile.get("present_sections")
    present = list(raw_present) if isinstance(raw_present, list) else []
    raw_missing = profile.get("missing_sections")
    missing = list(raw_missing) if isinstance(raw_missing, list) else []
    if required:
        doc.add_paragraph(f"Required sections: {', '.join(str(x) for x in required)}")
        doc.add_paragraph(f"Present sections: {', '.join(str(x) for x in present) or '-'}")
        if missing:
            doc.add_paragraph(f"Missing sections: {', '.join(str(x) for x in missing)}")


def _add_export_contract_section(doc: Document, contract: Dict[str, Any]) -> None:
    doc.add_heading("Export Contract Check", level=1)
    status = str(contract.get("status") or "warning").upper()
    doc.add_paragraph(f"Status: {status}")

    missing_sections = contract.get("missing_required_sections")
    if isinstance(missing_sections, list) and missing_sections:
        doc.add_paragraph(f"Missing required ToC sections: {', '.join(str(x) for x in missing_sections)}")
    else:
        doc.add_paragraph("Missing required ToC sections: none")

    expected_docx_headings = contract.get("expected_docx_headings")
    if isinstance(expected_docx_headings, list) and expected_docx_headings:
        doc.add_paragraph(f"Expected donor headings: {', '.join(str(x) for x in expected_docx_headings)}")

    missing_headers = contract.get("missing_required_primary_sheet_headers")
    if isinstance(missing_headers, list) and missing_headers:
        doc.add_paragraph(f"Missing required primary sheet headers: {', '.join(str(x) for x in missing_headers)}")

    warnings = contract.get("warnings")
    if isinstance(warnings, list) and warnings:
        doc.add_paragraph(f"Warnings: {', '.join(str(x) for x in warnings)}")


def build_docx_from_toc(
    toc_draft: Dict[str, Any],
    donor_id: str,
    logframe_draft: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
    quality_summary: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Конвертирует ToC draft в форматированный .docx."""
    doc = Document()

    title = doc.add_heading(f"Theory of Change — {donor_id}", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"Donor: {donor_id}")
    doc.add_paragraph("Generated by: GrantFlow")

    toc_content = _toc_root(toc_draft, donor_id)
    profile = build_export_template_profile(donor_id=donor_id, toc_payload=toc_content)
    contract = evaluate_export_contract(donor_id=donor_id, toc_payload=toc_content)
    _add_template_profile_section(doc, profile)
    _add_export_contract_section(doc, contract)
    _add_quality_summary_section(doc, quality_summary or {})
    _add_review_readiness_section(
        doc,
        quality_summary=quality_summary or {},
        citations=citations or toc_draft.get("citations") or [],
        critic_findings=critic_findings or [],
        review_comments=review_comments or [],
    )

    donor_key = normalize_export_template_key(donor_id)
    if donor_key == "usaid":
        _render_usaid_toc(doc, toc_content, logframe_draft=logframe_draft)
    elif donor_key == "eu":
        _render_eu_toc(doc, toc_content, logframe_draft=logframe_draft)
    elif donor_key == "worldbank":
        _render_worldbank_toc(doc, toc_content, logframe_draft=logframe_draft)
    elif donor_key == "giz":
        _render_giz_toc(doc, toc_content, logframe_draft=logframe_draft)
    elif donor_key == "un_agencies":
        _render_un_agencies_toc(doc, toc_content, logframe_draft=logframe_draft)
    elif donor_key in {"state_department", "us_state_department", "u.s. department of state", "us department of state"}:
        _render_state_department_toc(doc, toc_content, logframe_draft=logframe_draft)
    else:
        _render_generic_toc(doc, toc_content)

    _add_mel_indicator_summary_section(doc, logframe_draft)
    _add_citation_traceability_section(doc, citations or toc_draft.get("citations") or [])
    _add_critic_findings_section(doc, critic_findings or [])
    _add_review_comments_section(doc, review_comments or [])

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.read()


def save_docx_to_file(
    toc_draft: Dict[str, Any],
    donor_id: str,
    output_path: str,
    logframe_draft: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
    quality_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Сохраняет .docx на диск."""
    content = build_docx_from_toc(
        toc_draft,
        donor_id,
        logframe_draft=logframe_draft,
        citations=citations,
        critic_findings=critic_findings,
        review_comments=review_comments,
        quality_summary=quality_summary,
    )
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path
