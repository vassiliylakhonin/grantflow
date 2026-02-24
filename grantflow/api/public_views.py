from __future__ import annotations

import difflib
import json
from enum import Enum
from typing import Any, Dict, Optional


def sanitize_for_public_response(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): sanitize_for_public_response(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_public_response(item) for item in value]
    return str(value)


def public_state_snapshot(state: Any) -> Any:
    if not isinstance(state, dict):
        return sanitize_for_public_response(state)

    redacted_state = {}
    for key, value in state.items():
        if key in {"strategy", "donor_strategy"}:
            continue
        redacted_state[str(key)] = sanitize_for_public_response(value)
    return redacted_state


def public_job_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    public_job: Dict[str, Any] = {}
    for key, value in job.items():
        if key in {"webhook_url", "webhook_secret", "job_events"}:
            continue
        if key == "state":
            public_job[key] = public_state_snapshot(value)
            continue
        public_job[str(key)] = sanitize_for_public_response(value)
    public_job["webhook_configured"] = bool(job.get("webhook_url"))
    return public_job


def public_job_citations_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    state = job.get("state")
    citations = []
    if isinstance(state, dict):
        raw = state.get("citations")
        if isinstance(raw, list):
            citations = [sanitize_for_public_response(item) for item in raw if isinstance(item, dict)]
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "citation_count": len(citations),
        "citations": citations,
    }


def _public_versions_from_state(state: Any) -> list[Dict[str, Any]]:
    if not isinstance(state, dict):
        return []
    raw = state.get("draft_versions")
    if not isinstance(raw, list):
        return []

    versions: list[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        version = {
            "version_id": str(item.get("version_id") or ""),
            "sequence": sanitize_for_public_response(item.get("sequence")),
            "section": sanitize_for_public_response(item.get("section")),
            "node": sanitize_for_public_response(item.get("node")),
            "iteration": sanitize_for_public_response(item.get("iteration")),
            "content": sanitize_for_public_response(item.get("content") or {}),
        }
        versions.append(version)
    return versions


def public_job_versions_payload(job_id: str, job: Dict[str, Any], section: Optional[str] = None) -> Dict[str, Any]:
    versions = _public_versions_from_state(job.get("state"))
    if section:
        versions = [v for v in versions if v.get("section") == section]
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "version_count": len(versions),
        "versions": versions,
    }


def public_job_diff_payload(
    job_id: str,
    job: Dict[str, Any],
    *,
    section: Optional[str] = None,
    from_version_id: Optional[str] = None,
    to_version_id: Optional[str] = None,
) -> Dict[str, Any]:
    versions = _public_versions_from_state(job.get("state"))
    if section:
        versions = [v for v in versions if v.get("section") == section]

    by_id = {str(v.get("version_id") or ""): v for v in versions if v.get("version_id")}
    selected_from = by_id.get(from_version_id or "") if from_version_id else None
    selected_to = by_id.get(to_version_id or "") if to_version_id else None

    if (from_version_id and not selected_from) or (to_version_id and not selected_to):
        return {
            "job_id": str(job_id),
            "status": str(job.get("status") or ""),
            "section": section,
            "has_diff": False,
            "error": "Requested version_id not found",
            "diff_text": "",
            "diff_lines": [],
        }

    if not selected_to and not selected_from:
        if len(versions) >= 2:
            selected_from, selected_to = versions[-2], versions[-1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "Need at least two versions to compute diff",
                "diff_text": "",
                "diff_lines": [],
            }
    elif selected_to is None and selected_from is not None:
        if len(versions) >= 1:
            selected_to = versions[-1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "Need at least one target version to compute diff",
                "diff_text": "",
                "diff_lines": [],
            }
    elif selected_from is None and selected_to is not None:
        # default to previous version before selected_to within filtered set
        idx = next((i for i, v in enumerate(versions) if v.get("version_id") == selected_to.get("version_id")), -1)
        if idx > 0:
            selected_from = versions[idx - 1]
        else:
            return {
                "job_id": str(job_id),
                "status": str(job.get("status") or ""),
                "section": section,
                "has_diff": False,
                "error": "No previous version found for requested to_version_id",
                "diff_text": "",
                "diff_lines": [],
            }

    from_content = (selected_from or {}).get("content") if selected_from else {}
    to_content = (selected_to or {}).get("content") if selected_to else {}
    from_text = json.dumps(from_content or {}, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
    to_text = json.dumps(to_content or {}, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
    diff_lines = list(
        difflib.unified_diff(
            from_text,
            to_text,
            fromfile=str((selected_from or {}).get("version_id") or "from"),
            tofile=str((selected_to or {}).get("version_id") or "to"),
            lineterm="",
        )
    )
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "section": section or (selected_to or {}).get("section"),
        "from_version_id": (selected_from or {}).get("version_id"),
        "to_version_id": (selected_to or {}).get("version_id"),
        "has_diff": True,
        "diff_text": "\n".join(diff_lines),
        "diff_lines": diff_lines,
    }


def public_job_events_payload(job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    raw_events = job.get("job_events")
    events: list[Dict[str, Any]] = []
    if isinstance(raw_events, list):
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            events.append(sanitize_for_public_response(item))
    return {
        "job_id": str(job_id),
        "status": str(job.get("status") or ""),
        "event_count": len(events),
        "events": events,
    }


def public_checkpoint_payload(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    public_checkpoint: Dict[str, Any] = {}
    for key, value in checkpoint.items():
        if key == "state_snapshot":
            continue
        public_checkpoint[str(key)] = sanitize_for_public_response(value)
    public_checkpoint["has_state_snapshot"] = "state_snapshot" in checkpoint
    return public_checkpoint
