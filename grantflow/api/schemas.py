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
