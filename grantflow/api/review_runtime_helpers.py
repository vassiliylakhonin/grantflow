from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Request

from grantflow.api.constants import CRITIC_FINDING_SLA_HOURS, REVIEW_COMMENT_DEFAULT_SLA_HOURS


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_plus_hours(base_ts: Optional[str], hours: int) -> str:
    base_dt = _parse_iso_utc(base_ts) or datetime.now(timezone.utc)
    return (base_dt + timedelta(hours=max(1, int(hours)))).isoformat()


def _finding_sla_hours(severity: Any, *, finding_sla_hours_override: Optional[Dict[str, int]] = None) -> int:
    token = str(severity or "").strip().lower()
    source = finding_sla_hours_override if isinstance(finding_sla_hours_override, dict) else CRITIC_FINDING_SLA_HOURS
    return int(source.get(token, source.get("medium", CRITIC_FINDING_SLA_HOURS["medium"])))


def _comment_sla_hours(
    *,
    linked_finding_severity: Optional[str] = None,
    finding_sla_hours_override: Optional[Dict[str, int]] = None,
    default_comment_sla_hours: Optional[int] = None,
) -> int:
    if linked_finding_severity:
        return _finding_sla_hours(linked_finding_severity, finding_sla_hours_override=finding_sla_hours_override)
    if isinstance(default_comment_sla_hours, int) and default_comment_sla_hours > 0:
        return int(default_comment_sla_hours)
    return int(REVIEW_COMMENT_DEFAULT_SLA_HOURS)


def _finding_actor_from_request(request: Request) -> str:
    for header in ("x-reviewer", "x-actor", "x-user", "x-user-id", "x-email"):
        value = str(request.headers.get(header) or "").strip()
        if value:
            return value[:120]
    return "api_user"
