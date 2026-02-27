# grantflow/exporters/word_builder.py

from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _citation_summary_line(citation: Dict[str, Any]) -> str:
    stage = citation.get("stage", "")
    ctype = citation.get("citation_type", "")
    used_for = citation.get("used_for", "")
    label = citation.get("label") or citation.get("source") or citation.get("namespace") or ""
    page = citation.get("page")
    chunk = citation.get("chunk")
    confidence = citation.get("citation_confidence")

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
        meta_bits = [
            f"version={finding.get('version_id')}" if finding.get("version_id") else None,
            f"finding_id={finding.get('finding_id')}" if finding.get("finding_id") else None,
            f"source={finding.get('source')}" if finding.get("source") else None,
        ]
        meta_bits = [m for m in meta_bits if m]
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
        meta_bits = [
            f"version={comment.get('version_id')}" if comment.get("version_id") else None,
            f"linked_finding_id={comment.get('linked_finding_id')}" if comment.get("linked_finding_id") else None,
            str(comment.get("ts")) if comment.get("ts") else None,
        ]
        meta_bits = [m for m in meta_bits if m]
        if meta_bits:
            doc.add_paragraph(" · ".join(meta_bits))


def _normalize_donor_id(donor_id: str) -> str:
    return str(donor_id or "").strip().lower()


def _toc_root(toc_draft: Dict[str, Any]) -> Dict[str, Any]:
    toc = toc_draft.get("toc")
    if isinstance(toc, dict):
        return toc
    return toc_draft if isinstance(toc_draft, dict) else {}


def _render_usaid_toc(doc: Document, toc: Dict[str, Any]) -> None:
    doc.add_heading("USAID Results Framework", level=1)
    goal = str(toc.get("project_goal") or "").strip()
    if goal:
        doc.add_heading("Project Goal", level=2)
        doc.add_paragraph(goal)

    do_list = toc.get("development_objectives")
    if isinstance(do_list, list) and do_list:
        doc.add_heading("Development Objectives", level=2)
        for do in do_list:
            if not isinstance(do, dict):
                continue
            do_id = str(do.get("do_id") or "").strip()
            do_title = str(do.get("description") or "").strip()
            doc.add_heading(f"{do_id or 'DO'} — {do_title or 'Development Objective'}", level=3)
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


def _render_eu_toc(doc: Document, toc: Dict[str, Any]) -> None:
    doc.add_heading("EU Intervention Logic", level=1)
    overall = toc.get("overall_objective")
    if isinstance(overall, dict):
        objective_id = str(overall.get("objective_id") or "").strip()
        title = str(overall.get("title") or "").strip()
        rationale = str(overall.get("rationale") or "").strip()
        doc.add_heading("Overall Objective", level=2)
        if objective_id or title:
            doc.add_paragraph(f"{objective_id or 'Objective'} — {title or '-'}")
        if rationale:
            doc.add_paragraph(rationale)
        return
    doc.add_paragraph("Overall objective is not provided in EU schema draft.")


def _render_worldbank_toc(doc: Document, toc: Dict[str, Any]) -> None:
    doc.add_heading("World Bank Results Framework", level=1)
    objectives = toc.get("objectives")
    if isinstance(objectives, list) and objectives:
        for obj in objectives:
            if not isinstance(obj, dict):
                continue
            objective_id = str(obj.get("objective_id") or "").strip()
            title = str(obj.get("title") or "").strip()
            description = str(obj.get("description") or "").strip()
            doc.add_heading(f"{objective_id or 'Objective'} — {title or '-'}", level=2)
            if description:
                doc.add_paragraph(description)
        return
    doc.add_paragraph("No World Bank objectives found in draft.")


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


def build_docx_from_toc(
    toc_draft: Dict[str, Any],
    donor_id: str,
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """Конвертирует ToC draft в форматированный .docx."""
    doc = Document()

    title = doc.add_heading(f"Theory of Change — {donor_id}", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"Donor: {donor_id}")
    doc.add_paragraph("Generated by: GrantFlow")

    donor_key = _normalize_donor_id(donor_id)
    toc_content = _toc_root(toc_draft)
    if donor_key == "usaid":
        _render_usaid_toc(doc, toc_content)
    elif donor_key == "eu":
        _render_eu_toc(doc, toc_content)
    elif donor_key == "worldbank":
        _render_worldbank_toc(doc, toc_content)
    else:
        _render_generic_toc(doc, toc_content)

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
    citations: Optional[List[Dict[str, Any]]] = None,
    critic_findings: Optional[List[Dict[str, Any]]] = None,
    review_comments: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Сохраняет .docx на диск."""
    content = build_docx_from_toc(
        toc_draft,
        donor_id,
        citations=citations,
        critic_findings=critic_findings,
        review_comments=review_comments,
    )
    with open(output_path, "wb") as f:
        f.write(content)
    return output_path
