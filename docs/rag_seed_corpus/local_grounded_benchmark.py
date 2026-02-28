#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

PRESET_CASES: dict[str, dict[str, Any]] = {
    "usaid": {
        "preset_key": "usaid_gov_ai_kazakhstan",
        "expected_doc_families": [
            "donor_policy",
            "responsible_ai_guidance",
            "country_context",
            "competency_framework",
        ],
        "payload": {
            "donor_id": "usaid",
            "input_context": {
                "project": "Responsible AI Skills for Civil Service Modernization in Kazakhstan",
                "country": "Kazakhstan",
                "region": "National with pilot cohorts in Astana and Almaty",
                "timeframe": "2026-2027 (24 months)",
                "problem": (
                    "Civil servants across participating government agencies have uneven practical skills "
                    "in safe, effective AI use for public administration workflows."
                ),
                "target_population": (
                    "Mid-level and senior civil servants in policy, service delivery, and digital transformation units."
                ),
                "expected_change": (
                    "Participating agencies adopt responsible AI practices, SOPs, and pilot AI-enabled workflows that "
                    "improve selected administrative processes and service quality."
                ),
                "key_activities": [
                    "needs assessment",
                    "curriculum development",
                    "cohort training",
                    "applied labs",
                    "SOP drafting",
                    "MEL tracking",
                ],
            },
        },
    },
    "eu": {
        "preset_key": "eu_digital_governance_moldova",
        "expected_doc_families": [
            "donor_results_guidance",
            "digital_governance_guidance",
            "country_context",
            "municipal_process_guidance",
        ],
        "payload": {
            "donor_id": "eu",
            "input_context": {
                "project": "Digital Governance and Service Delivery Improvement",
                "country": "Moldova",
                "region": "Selected municipalities and central support agencies",
                "timeframe": "2026-2028 (36 months)",
                "problem": (
                    "Public institutions and municipalities face uneven capacity to manage digital service reform, "
                    "process quality, and performance monitoring."
                ),
                "target_population": (
                    "Municipal service teams, process owners, supervisors, and digital governance support units."
                ),
                "expected_change": (
                    "Participating institutions improve service process quality and digitization implementation through "
                    "stronger intervention logic, process management, and performance routines."
                ),
                "key_activities": [
                    "intervention logic workshops",
                    "service/process diagnostics",
                    "capacity development for process owners",
                    "municipal process pilots",
                    "service quality monitoring routines",
                ],
            },
        },
    },
    "worldbank": {
        "preset_key": "worldbank_public_sector_uzbekistan",
        "expected_doc_families": [
            "donor_results_guidance",
            "project_reference_docs",
            "country_context",
            "agency_process_docs",
        ],
        "payload": {
            "donor_id": "worldbank",
            "input_context": {
                "project": "Public Sector Performance and Service Delivery Capacity Strengthening",
                "country": "Uzbekistan",
                "region": "National ministries and selected subnational administrations",
                "timeframe": "2026-2028 (36 months)",
                "problem": (
                    "Public agencies have uneven capabilities in performance management and evidence-based "
                    "decision-making for service delivery improvement."
                ),
                "target_population": (
                    "Government managers and civil servants in reform, performance, and service delivery functions."
                ),
                "expected_change": (
                    "Participating institutions adopt stronger performance management practices and improve selected "
                    "services through diagnostics, process improvement pilots, and adaptive reviews."
                ),
                "key_activities": [
                    "institutional diagnostics and process mapping",
                    "capacity development for performance management and data use",
                    "technical assistance for service improvement plans",
                    "process optimization pilots",
                    "adaptive performance reviews",
                ],
            },
        },
    },
    "giz": {
        "preset_key": "giz_sme_resilience_jordan",
        "expected_doc_families": [
            "donor_policy",
            "implementation_reference",
            "country_context",
            "sustainability_guidance",
        ],
        "payload": {
            "donor_id": "giz",
            "input_context": {
                "project": "SME and Youth Employment Resilience through TVET-Industry Partnerships",
                "country": "Jordan",
                "region": "Northern and central governorates",
                "timeframe": "2026-2028 (30 months)",
                "problem": (
                    "SMEs and youth employment programs face gaps in practical skills alignment, "
                    "business support quality, and institutionalized implementation routines."
                ),
                "target_population": (
                    "Youth job-seekers, SME owners/managers, and partner institutions responsible for "
                    "skills development and enterprise support."
                ),
                "expected_change": (
                    "Partner institutions and service providers apply stronger implementation routines, "
                    "improve employability support, and sustain results through institutional adoption."
                ),
                "key_activities": [
                    "joint diagnostics with partner institutions",
                    "training-of-trainers for service providers",
                    "SME coaching and market linkage support",
                    "institutional SOP rollout and follow-up mentoring",
                    "results monitoring and adaptive learning reviews",
                ],
            },
        },
    },
    "state_department": {
        "preset_key": "state_department_media_georgia",
        "expected_doc_families": [
            "donor_policy",
            "country_context",
            "risk_context",
            "implementation_reference",
        ],
        "payload": {
            "donor_id": "state_department",
            "input_context": {
                "project": "Independent Media Resilience and Civic Information Integrity",
                "country": "Georgia",
                "region": "National with regional media hubs",
                "timeframe": "2026-2028 (24 months)",
                "problem": (
                    "Independent media and civic information ecosystems face sustained pressure from "
                    "disinformation, legal uncertainty, and uneven institutional resilience."
                ),
                "target_population": (
                    "Independent journalists, media editors, civic communicators, and local partner organizations."
                ),
                "expected_change": (
                    "Media and civic actors strengthen professional practice, risk mitigation, and coordinated "
                    "response mechanisms that protect information integrity."
                ),
                "key_activities": [
                    "editorial resilience and legal-risk training",
                    "collaborative fact-checking and verification routines",
                    "grants for audience engagement and safety protocols",
                    "stakeholder coordination with civic and legal support actors",
                    "monitoring of media integrity and response outcomes",
                ],
            },
        },
    },
}


def _json_request(
    method: str,
    url: str,
    *,
    payload: Optional[dict[str, Any]] = None,
    api_key: Optional[str] = None,
    timeout: float = 120.0,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc


def _poll_job(base_url: str, job_id: str, *, api_key: Optional[str], timeout_s: int, sleep_s: float) -> dict[str, Any]:
    started = time.time()
    while True:
        status = _json_request("GET", f"{base_url}/status/{job_id}", api_key=api_key)
        state = str(status.get("status") or "")
        if state in {"done", "error", "canceled"}:
            return status
        if time.time() - started > timeout_s:
            raise TimeoutError(f"Timed out waiting for job {job_id} after {timeout_s}s (last status={state})")
        time.sleep(sleep_s)


def _inventory_readiness(
    base_url: str, donor_id: str, expected_doc_families: list[str], *, api_key: Optional[str]
) -> dict[str, Any]:
    qs = urllib.parse.urlencode({"donor_id": donor_id})
    payload = _json_request("GET", f"{base_url}/ingest/inventory?{qs}", api_key=api_key)
    present_counts = payload.get("doc_family_counts") if isinstance(payload.get("doc_family_counts"), dict) else {}
    present = sorted([k for k, v in present_counts.items() if int(v or 0) > 0])
    missing = [f for f in expected_doc_families if f not in present]
    loaded = sum(1 for f in expected_doc_families if f in present)
    return {
        "inventory": payload,
        "present_doc_families": present,
        "missing_doc_families": missing,
        "expected_doc_families": expected_doc_families,
        "coverage_rate": round(loaded / len(expected_doc_families), 4) if expected_doc_families else None,
    }


def run_case(
    base_url: str,
    donor_id: str,
    *,
    api_key: Optional[str],
    llm_mode: bool,
    hitl_enabled: bool,
    timeout_s: int,
    sleep_s: float,
) -> dict[str, Any]:
    preset = PRESET_CASES[donor_id]
    readiness = _inventory_readiness(base_url, donor_id, preset["expected_doc_families"], api_key=api_key)
    payload = dict(preset["payload"])
    payload["llm_mode"] = bool(llm_mode)
    payload["hitl_enabled"] = bool(hitl_enabled)
    payload["client_metadata"] = {
        "preset_key": preset["preset_key"],
        "rag_readiness": {"expected_doc_families": list(preset["expected_doc_families"])},
    }

    started = _json_request("POST", f"{base_url}/generate", payload=payload, api_key=api_key)
    job_id = str(started.get("job_id") or started.get("id") or "")
    if not job_id:
        raise RuntimeError(f"Generate response missing job_id for donor {donor_id}: {started}")

    final_status = _poll_job(base_url, job_id, api_key=api_key, timeout_s=timeout_s, sleep_s=sleep_s)
    quality = _json_request("GET", f"{base_url}/status/{job_id}/quality", api_key=api_key)
    citations = _json_request("GET", f"{base_url}/status/{job_id}/citations", api_key=api_key)
    citation_rows = citations.get("citations") if isinstance(citations.get("citations"), list) else []
    citation_types: dict[str, int] = {}
    for row in citation_rows:
        if not isinstance(row, dict):
            continue
        ct = str(row.get("citation_type") or "unknown")
        citation_types[ct] = citation_types.get(ct, 0) + 1

    return {
        "donor_id": donor_id,
        "job_id": job_id,
        "status": str(final_status.get("status") or ""),
        "readiness": readiness,
        "quality": quality,
        "citation_type_counts": citation_types,
    }


def _fmt_num(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if value is None:
        return "-"
    return str(value)


def print_summary(results: list[dict[str, Any]]) -> None:
    print("\nGrounded benchmark summary")
    header = [
        "donor",
        "status",
        "q",
        "critic",
        "retr_hits",
        "citations",
        "fallback_ns",
        "rag_low",
        "low_conf",
        "conf_avg",
        "thr_hit",
        "readiness",
    ]
    print(" | ".join(header))
    print(" | ".join(["---"] * len(header)))
    for row in results:
        q = row.get("quality") if isinstance(row.get("quality"), dict) else {}
        cit = q.get("citations") if isinstance(q.get("citations"), dict) else {}
        arch = q.get("architect") if isinstance(q.get("architect"), dict) else {}
        ready = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}
        exp = ready.get("expected_doc_families") if isinstance(ready.get("expected_doc_families"), list) else []
        missing = ready.get("missing_doc_families") if isinstance(ready.get("missing_doc_families"), list) else []
        loaded = (len(exp) - len(missing)) if exp else 0
        readiness_str = f"{loaded}/{len(exp)}"
        print(
            " | ".join(
                [
                    str(row.get("donor_id") or ""),
                    str(row.get("status") or ""),
                    _fmt_num(q.get("quality_score")),
                    _fmt_num(q.get("critic_score")),
                    _fmt_num(arch.get("retrieval_hits_count")),
                    _fmt_num(cit.get("citation_count")),
                    _fmt_num(cit.get("fallback_namespace_citation_count")),
                    _fmt_num(cit.get("rag_low_confidence_citation_count")),
                    _fmt_num(cit.get("low_confidence_citation_count")),
                    _fmt_num(cit.get("citation_confidence_avg")),
                    _fmt_num(cit.get("architect_threshold_hit_rate")),
                    readiness_str,
                ]
            )
        )
    print("")
    for row in results:
        print(
            f"- {row['donor_id']} job_id={row['job_id']} citation_types={json.dumps(row['citation_type_counts'], sort_keys=True)}"
        )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local grounded benchmark against GrantFlow API for governance presets."
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="GrantFlow API base URL.")
    parser.add_argument("--api-key", default="", help="Optional X-API-Key.")
    parser.add_argument(
        "--donors",
        default="usaid,eu,worldbank,giz,state_department",
        help="Comma-separated donors from preset set: usaid,eu,worldbank,giz,state_department",
    )
    parser.add_argument("--llm-mode", action="store_true", help="Run with llm_mode=true (default false).")
    parser.add_argument("--hitl-enabled", action="store_true", help="Run with hitl_enabled=true (default false).")
    parser.add_argument("--timeout-s", type=int, default=180, help="Per-job polling timeout in seconds.")
    parser.add_argument("--sleep-s", type=float, default=1.0, help="Poll interval in seconds.")
    parser.add_argument("--json-out", default="", help="Optional path to write raw benchmark results JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    donors = [d.strip().lower() for d in str(args.donors or "").split(",") if d.strip()]
    unknown = [d for d in donors if d not in PRESET_CASES]
    if unknown:
        print(f"Unknown donor presets: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not donors:
        print("No donors selected.", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for donor_id in donors:
        print(f"[run] donor={donor_id} llm_mode={bool(args.llm_mode)} hitl_enabled={bool(args.hitl_enabled)}")
        result = run_case(
            args.api_base.rstrip("/"),
            donor_id,
            api_key=(args.api_key or None),
            llm_mode=bool(args.llm_mode),
            hitl_enabled=bool(args.hitl_enabled),
            timeout_s=int(args.timeout_s),
            sleep_s=float(args.sleep_s),
        )
        results.append(result)

    print_summary(results)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
