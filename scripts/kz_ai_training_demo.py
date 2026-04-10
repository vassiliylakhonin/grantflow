#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "").strip()
TIMEOUT_SEC = int(os.getenv("KZ_DEMO_TIMEOUT_SEC", "300"))
POLL_SEC = float(os.getenv("KZ_DEMO_POLL_SEC", "2"))
OUT_DIR = Path(os.getenv("KZ_DEMO_OUT_DIR", "build/kz-ai-demo"))
PDF_DIR = Path(os.getenv("KZ_DEMO_PDF_DIR", "build/kz_ai_training_seed_pdfs"))
DONOR_ID = os.getenv("KZ_DEMO_DONOR_ID", "un_agencies")
TENANT_ID = os.getenv("KZ_DEMO_TENANT_ID", f"kz-ai-demo-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")


CASE_INPUT_CONTEXT: Dict[str, Any] = {
    "project": "AI Literacy & Safe Use Training for Civil Servants of Kazakhstan",
    "country": "Kazakhstan",
    "problem": "Civil servants have uneven practical AI skills and limited guidance on safe, policy-aligned use in public service workflows.",
    "expected_change": "Government teams apply AI tools responsibly to improve service quality, speed, and consistency while managing data/privacy risks.",
    "activities": [
        "Baseline skills assessment",
        "Role-based training modules",
        "Hands-on labs for public service use-cases",
        "Train-the-trainer program",
        "Governance and risk playbook rollout",
    ],
    "duration_months": 12,
    "budget_usd": 450000,
}

SEED_DOCS: Dict[str, str] = {
    "kz_ai_public_sector_policy_outline.pdf": """
Kazakhstan public sector AI policy outline.
Purpose: enable safe and effective AI use in government services.
Principles: legality, transparency, human oversight, data minimization, accountability.
Implementation domains: citizen service portals, document triage, call-center assistance, analytics.
Risk controls: personal data protection, model monitoring, incident reporting, role-based access.
Training implications: all civil servants need baseline AI literacy and policy awareness.
""",
    "kz_civil_service_ai_competency_framework.pdf": """
Civil service AI competency framework for Kazakhstan.
Level 1: AI fundamentals, prompt basics, identifying model limitations.
Level 2: workflow integration, quality checks, source validation.
Level 3: governance leadership, risk registers, procurement oversight.
Assessment: pre-test and post-test with minimum 30 percent improvement target.
""",
    "kz_ai_training_curriculum_module_plan.pdf": """
AI training curriculum for public servants.
Module 1: Intro to AI in public administration.
Module 2: Responsible data handling and privacy.
Module 3: Practical use-cases in permits, social support, and correspondence processing.
Module 4: Human-in-the-loop decisions and escalation rules.
Module 5: Monitoring outcomes and avoiding automation bias.
""",
    "kz_ai_governance_and_compliance_checklist.pdf": """
Governance checklist for AI-enabled public services.
Checklist includes: legal basis documented, DPIA completed, data retention policy aligned,
quality review owner assigned, fallback manual process defined,
citizen complaint channel active, monthly audit report produced.
Compliance scorecard target: at least 95 percent checklist completion before production use.
""",
    "kz_public_service_ai_pilot_kpi_baseline.pdf": """
Pilot KPI baseline template.
Primary KPIs: cycle time reduction 30 to 50 percent,
review loop reduction 20 to 40 percent,
compliance completeness at least 95 percent,
traceability coverage at least 90 percent for critical claims.
Secondary KPIs: reviewer time savings, fewer late-stage rewrites.
""",
    "kz_train_the_trainer_rollout_plan.pdf": """
Train-the-trainer rollout for ministries and akimats.
Cohort model: 25 lead trainers, each cascading to 40 staff.
Delivery format: blended workshops and supervised labs.
Success condition: at least two internal trainers certified per participating agency.
Sustainability: quarterly refresher and model policy update briefings.
""",
}


def _headers(content_type_json: bool = False) -> Dict[str, str]:
    h: Dict[str, str] = {}
    if content_type_json:
        h["Content-Type"] = "application/json"
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _get(path: str) -> Dict[str, Any]:
    req = urllib.request.Request(f"{API_BASE}{path}", method="GET", headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        method="POST",
        headers=_headers(content_type_json=True),
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_job(job_id: str) -> str:
    end = time.time() + TIMEOUT_SEC
    status = ""
    while time.time() < end:
        cur = _get(f"/status/{job_id}")
        status = str(cur.get("status") or "").lower()
        if status in {"done", "error", "failed", "canceled"}:
            return status
        time.sleep(max(0.5, POLL_SEC))
    return status or "timeout"


def _run_case(llm_mode: bool) -> Dict[str, Any]:
    payload = {
        "donor_id": DONOR_ID,
        "tenant_id": TENANT_ID,
        "llm_mode": llm_mode,
        "hitl_enabled": False,
        "architect_rag_enabled": True,
        "strict_preflight": False,
        "input_context": CASE_INPUT_CONTEXT,
    }
    accepted = _post_json("/generate", payload)
    job_id = str(accepted.get("job_id") or "")
    if not job_id:
        raise RuntimeError("missing job_id")
    status = _wait_job(job_id)
    metrics = _get(f"/status/{job_id}/metrics")
    quality = _get(f"/status/{job_id}/quality")
    events = _get(f"/status/{job_id}/events")
    export_payload = _get(f"/status/{job_id}/export-payload")
    trust = (metrics.get("grounding_trust_summary") or {})
    readiness = ((export_payload.get("payload") or {}).get("submission_package_readiness") or {})
    return {
        "job_id": job_id,
        "status": status,
        "terminal_status": metrics.get("terminal_status"),
        "quality_score": quality.get("quality_score"),
        "critic_score": quality.get("critic_score"),
        "trust_score": trust.get("trust_score"),
        "trust_level": trust.get("trust_level"),
        "grounding_risk_level": metrics.get("grounding_risk_level"),
        "citation_count": metrics.get("citation_count"),
        "retrieval_grounded_citation_rate": metrics.get("retrieval_grounded_citation_rate"),
        "pilot_success_kpis_present": bool(metrics.get("pilot_success_kpis")),
        "readiness_status": readiness.get("readiness_status"),
        "top_gap": readiness.get("top_gap"),
        "last_event_types": [e.get("type") for e in (events.get("events") or [])[-3:]],
    }


def _ensure_reportlab() -> None:
    try:
        import reportlab  # noqa: F401
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])


def _build_seed_pdfs() -> list[Path]:
    _ensure_reportlab()
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for name, body in SEED_DOCS.items():
        path = PDF_DIR / name
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica", 11)
        for line in textwrap.dedent(body).strip().splitlines():
            line = line.strip()
            if not line:
                y -= 14
                continue
            chunks = [line[i : i + 95] for i in range(0, len(line), 95)]
            for chunk in chunks:
                c.drawString(40, y, chunk)
                y -= 14
                if y < 60:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - 50
        c.save()
        out.append(path)
    return out


def _ingest_pdf(path: Path) -> None:
    cmd = [
        "curl",
        "-fsS",
        "-X",
        "POST",
        "-F",
        f"donor_id={DONOR_ID}",
        "-F",
        f"tenant_id={TENANT_ID}",
        "-F",
        f"file=@{path};type=application/pdf",
        f"{API_BASE}/ingest",
    ]
    if API_KEY:
        cmd[1:1] = ["-H", f"X-API-Key: {API_KEY}"]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)


def _delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    def num(v: Any) -> Optional[float]:
        return float(v) if isinstance(v, (int, float)) else None

    bq, aq = num(before.get("quality_score")), num(after.get("quality_score"))
    bt, at = num(before.get("trust_score")), num(after.get("trust_score"))
    return {
        "quality_score_delta": (aq - bq) if aq is not None and bq is not None else None,
        "trust_score_delta": (at - bt) if at is not None and bt is not None else None,
        "grounding_risk_before": before.get("grounding_risk_level"),
        "grounding_risk_after": after.get("grounding_risk_level"),
        "retrieval_rate_before": before.get("retrieval_grounded_citation_rate"),
        "retrieval_rate_after": after.get("retrieval_grounded_citation_rate"),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _get("/health")
    _get("/ready")

    baseline = _run_case(llm_mode=True)

    pdfs = _build_seed_pdfs()
    for pdf in pdfs:
        _ingest_pdf(pdf)

    improved = _run_case(llm_mode=True)

    result = {
        "api_base": API_BASE,
        "donor_id": DONOR_ID,
        "tenant_id": TENANT_ID,
        "seed_pdf_count": len(pdfs),
        "baseline": baseline,
        "after_ingest": improved,
        "delta": _delta(baseline, improved),
    }

    (OUT_DIR / "kz_ai_demo_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# KZ AI Training Demo Validation",
        "",
        f"- API: `{API_BASE}`",
        f"- donor_id: `{DONOR_ID}`",
        f"- tenant_id: `{TENANT_ID}`",
        f"- seeded PDFs: `{len(pdfs)}`",
        "",
        "## Baseline (before ingest)",
        f"- job_id: `{baseline['job_id']}`",
        f"- status: `{baseline['status']}`",
        f"- quality_score: `{baseline['quality_score']}`",
        f"- trust_score: `{baseline['trust_score']}` ({baseline['trust_level']})",
        f"- grounding_risk_level: `{baseline['grounding_risk_level']}`",
        f"- retrieval_grounded_citation_rate: `{baseline['retrieval_grounded_citation_rate']}`",
        "",
        "## After ingest",
        f"- job_id: `{improved['job_id']}`",
        f"- status: `{improved['status']}`",
        f"- quality_score: `{improved['quality_score']}`",
        f"- trust_score: `{improved['trust_score']}` ({improved['trust_level']})",
        f"- grounding_risk_level: `{improved['grounding_risk_level']}`",
        f"- retrieval_grounded_citation_rate: `{improved['retrieval_grounded_citation_rate']}`",
        "",
        "## Delta",
        f"- quality_score_delta: `{result['delta']['quality_score_delta']}`",
        f"- trust_score_delta: `{result['delta']['trust_score_delta']}`",
        f"- grounding_risk: `{result['delta']['grounding_risk_before']}` -> `{result['delta']['grounding_risk_after']}`",
        f"- retrieval_rate: `{result['delta']['retrieval_rate_before']}` -> `{result['delta']['retrieval_rate_after']}`",
        "",
        f"Raw JSON: `{OUT_DIR / 'kz_ai_demo_result.json'}`",
    ]
    (OUT_DIR / "kz_ai_demo_result.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"kz_ai_demo: PASS ({OUT_DIR / 'kz_ai_demo_result.json'})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"kz_ai_demo: FAIL (API unreachable: {exc})", file=sys.stderr)
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        print(f"kz_ai_demo: FAIL (command exit={exc.returncode})", file=sys.stderr)
        raise SystemExit(3)
    except Exception as exc:
        print(f"kz_ai_demo: FAIL ({exc})", file=sys.stderr)
        raise SystemExit(1)
