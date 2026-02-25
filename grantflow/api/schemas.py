from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class JobStatusPublicResponse(BaseModel):
    status: str
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    checkpoint_id: Optional[str] = None
    checkpoint_stage: Optional[str] = None
    checkpoint_status: Optional[str] = None
    resume_from: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class CitationPublicResponse(BaseModel):
    stage: Optional[str] = None
    citation_type: Optional[str] = None
    namespace: Optional[str] = None
    statement_path: Optional[str] = None
    statement: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    chunk: Optional[int] = None
    chunk_id: Optional[str] = None
    used_for: Optional[str] = None
    label: Optional[str] = None
    excerpt: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobCitationsPublicResponse(BaseModel):
    job_id: str
    status: str
    citation_count: int
    citations: list[CitationPublicResponse]

    model_config = ConfigDict(extra="allow")


class DraftVersionPublicResponse(BaseModel):
    version_id: str
    sequence: Optional[int] = None
    section: Optional[str] = None
    node: Optional[str] = None
    iteration: Optional[int] = None
    content: Dict[str, Any] = {}

    model_config = ConfigDict(extra="allow")


class JobVersionsPublicResponse(BaseModel):
    job_id: str
    status: str
    version_count: int
    versions: list[DraftVersionPublicResponse]

    model_config = ConfigDict(extra="allow")


class JobDiffPublicResponse(BaseModel):
    job_id: str
    status: str
    section: Optional[str] = None
    from_version_id: Optional[str] = None
    to_version_id: Optional[str] = None
    has_diff: bool
    error: Optional[str] = None
    diff_text: str
    diff_lines: list[str]

    model_config = ConfigDict(extra="allow")


class JobEventPublicResponse(BaseModel):
    event_id: str
    ts: str
    type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobEventsPublicResponse(BaseModel):
    job_id: str
    status: str
    event_count: int
    events: list[JobEventPublicResponse]

    model_config = ConfigDict(extra="allow")


class JobMetricsPublicResponse(BaseModel):
    job_id: str
    status: str
    event_count: int
    status_change_count: int
    pause_count: int
    resume_count: int
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    first_pending_hitl_at: Optional[str] = None
    terminal_at: Optional[str] = None
    terminal_status: Optional[str] = None
    time_to_first_draft_seconds: Optional[float] = None
    time_to_terminal_seconds: Optional[float] = None
    time_in_pending_hitl_seconds: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class ReviewCommentPublicResponse(BaseModel):
    comment_id: str
    ts: str
    section: str
    status: str
    message: str
    author: Optional[str] = None
    version_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobCommentsPublicResponse(BaseModel):
    job_id: str
    status: str
    comment_count: int
    comments: list[ReviewCommentPublicResponse]

    model_config = ConfigDict(extra="allow")


class CriticRuleCheckPublicResponse(BaseModel):
    code: str
    status: str
    section: str
    detail: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class CriticFatalFlawPublicResponse(BaseModel):
    code: str
    severity: str
    section: str
    version_id: Optional[str] = None
    message: str
    fix_hint: Optional[str] = None
    source: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobCriticPublicResponse(BaseModel):
    job_id: str
    status: str
    quality_score: Optional[float] = None
    critic_score: Optional[float] = None
    engine: Optional[str] = None
    rule_score: Optional[float] = None
    llm_score: Optional[float] = None
    needs_revision: Optional[bool] = None
    revision_instructions: Optional[str] = None
    fatal_flaw_count: int
    fatal_flaws: list[CriticFatalFlawPublicResponse]
    fatal_flaw_messages: list[str]
    rule_check_count: int
    rule_checks: list[CriticRuleCheckPublicResponse]

    model_config = ConfigDict(extra="allow")


class PortfolioMetricsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


class PortfolioMetricsPublicResponse(BaseModel):
    job_count: int
    filters: PortfolioMetricsFiltersPublicResponse
    status_counts: Dict[str, int]
    donor_counts: Dict[str, int]
    terminal_job_count: int
    hitl_job_count: int
    total_pause_count: int
    total_resume_count: int
    avg_time_to_first_draft_seconds: Optional[float] = None
    avg_time_to_terminal_seconds: Optional[float] = None
    avg_time_in_pending_hitl_seconds: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class HITLPendingCheckpointPublicResponse(BaseModel):
    id: str
    stage: str
    status: str
    donor_id: str
    feedback: Optional[str] = None
    has_state_snapshot: bool

    model_config = ConfigDict(extra="allow")


class HITLPendingListPublicResponse(BaseModel):
    pending_count: int
    checkpoints: list[HITLPendingCheckpointPublicResponse]

    model_config = ConfigDict(extra="allow")
