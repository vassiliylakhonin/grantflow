from __future__ import annotations

REVIEW_COMMENT_SECTIONS = {"toc", "logframe", "general"}
REVIEW_COMMENT_STATUSES = {"open", "acknowledged", "resolved"}
CRITIC_FINDING_STATUSES = {"open", "acknowledged", "resolved"}
CRITIC_FINDING_SLA_HOURS = {"high": 24, "medium": 72, "low": 120}
REVIEW_COMMENT_DEFAULT_SLA_HOURS = 72
TERMINAL_JOB_STATUSES = {"done", "error", "canceled"}
STATUS_WEBHOOK_EVENTS = {
    "running": "job.started",
    "pending_hitl": "job.pending_hitl",
    "done": "job.completed",
    "error": "job.failed",
    "canceled": "job.canceled",
}
RUNTIME_PIPELINE_STATE_KEYS = {
    "_start_at",
    "hitl_checkpoint_stage",
    "hitl_resume_from",
    "hitl_checkpoint_id",
}
HITL_HISTORY_EVENT_TYPES = {
    "status_changed",
    "resume_requested",
    "hitl_checkpoint_published",
    "hitl_checkpoint_decision",
    "hitl_checkpoint_canceled",
}
GROUNDING_POLICY_MODES = {"off", "warn", "strict"}
GENERATE_PREFLIGHT_DEFAULT_DOC_FAMILIES: dict[str, list[str]] = {
    "usaid": ["donor_policy", "responsible_ai_guidance", "country_context"],
    "eu": ["donor_results_guidance", "digital_governance_guidance", "country_context"],
    "worldbank": ["donor_results_guidance", "project_reference_docs", "country_context"],
    "giz": ["donor_policy", "country_context", "implementation_reference"],
    "state_department": ["donor_policy", "country_context", "risk_context"],
    "us_state_department": ["donor_policy", "country_context", "risk_context"],
}
PREFLIGHT_CRITICAL_DOC_FAMILY_MIN_UPLOADS: dict[str, int] = {
    "donor_policy": 2,
    "compliance_requirements": 2,
    "eligibility_rules": 2,
}
