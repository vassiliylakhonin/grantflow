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
    doc_id: Optional[str] = None
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
    citation_confidence: Optional[float] = None
    evidence_score: Optional[float] = None
    evidence_rank: Optional[int] = None
    retrieval_rank: Optional[int] = None
    retrieval_confidence: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobCitationsPublicResponse(BaseModel):
    job_id: str
    status: str
    citation_count: int
    citations: list[CitationPublicResponse]

    model_config = ConfigDict(extra="allow")


class JobExportPayloadPublicResponse(BaseModel):
    job_id: str
    status: str
    payload: Dict[str, Any]

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
    retrieval_expected: Optional[bool] = None
    grounding_risk_level: Optional[str] = None
    citation_count: Optional[int] = None
    fallback_namespace_citation_count: Optional[int] = None
    strategy_reference_citation_count: Optional[int] = None
    retrieval_grounded_citation_count: Optional[int] = None
    non_retrieval_citation_count: Optional[int] = None
    retrieval_grounded_citation_rate: Optional[float] = None
    non_retrieval_citation_rate: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class ReviewCommentPublicResponse(BaseModel):
    comment_id: str
    ts: str
    section: str
    status: str
    message: str
    author: Optional[str] = None
    version_id: Optional[str] = None
    linked_finding_id: Optional[str] = None
    due_at: Optional[str] = None
    sla_hours: Optional[int] = None
    workflow_state: Optional[str] = None
    is_overdue: Optional[bool] = None
    age_hours: Optional[float] = None
    time_to_due_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobCommentsPublicResponse(BaseModel):
    job_id: str
    status: str
    comment_count: int
    comments: list[ReviewCommentPublicResponse]

    model_config = ConfigDict(extra="allow")


class ReviewWorkflowTimelineEventPublicResponse(BaseModel):
    event_id: Optional[str] = None
    ts: Optional[str] = None
    type: str
    kind: Optional[str] = None
    finding_id: Optional[str] = None
    comment_id: Optional[str] = None
    status: Optional[str] = None
    section: Optional[str] = None
    severity: Optional[str] = None
    actor: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSummaryPublicResponse(BaseModel):
    finding_count: int
    comment_count: int
    linked_comment_count: int
    orphan_linked_comment_count: int
    open_finding_count: int
    acknowledged_finding_count: int
    resolved_finding_count: int
    pending_finding_count: int = 0
    overdue_finding_count: int = 0
    open_comment_count: int
    resolved_comment_count: int
    pending_comment_count: int = 0
    overdue_comment_count: int = 0
    finding_status_counts: Dict[str, int]
    finding_severity_counts: Dict[str, int]
    comment_status_counts: Dict[str, int]
    timeline_event_count: int
    last_activity_at: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowFiltersPublicResponse(BaseModel):
    event_type: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowPublicResponse(BaseModel):
    job_id: str
    status: str
    filters: JobReviewWorkflowFiltersPublicResponse
    summary: JobReviewWorkflowSummaryPublicResponse
    findings: list[CriticFatalFlawPublicResponse]
    comments: list[ReviewCommentPublicResponse]
    timeline: list[ReviewWorkflowTimelineEventPublicResponse]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowTrendPointPublicResponse(BaseModel):
    bucket: str
    count: int

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowTrendsPublicResponse(BaseModel):
    job_id: str
    status: str
    generated_at: str
    filters: JobReviewWorkflowFiltersPublicResponse
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    timeline_event_count: int = 0
    top_event_type: Optional[str] = None
    top_event_type_count: Optional[int] = None
    total_series: list[JobReviewWorkflowTrendPointPublicResponse]
    event_type_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    kind_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    status_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAItemPublicResponse(BaseModel):
    kind: str
    id: str
    section: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    due_at: Optional[str] = None
    overdue_hours: Optional[float] = None
    message: Optional[str] = None
    linked_finding_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAFiltersPublicResponse(BaseModel):
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLATrendPointPublicResponse(BaseModel):
    bucket: str
    count: int

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLATrendsPublicResponse(BaseModel):
    job_id: str
    status: str
    generated_at: str
    filters: JobReviewWorkflowSLAFiltersPublicResponse
    overdue_after_hours: int
    overdue_finding_count: int
    overdue_comment_count: int
    overdue_total: int
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    total_series: list[JobReviewWorkflowSLATrendPointPublicResponse]
    severity_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAHotspotsFiltersPublicResponse(BaseModel):
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None
    top_limit: Optional[int] = None
    hotspot_kind: Optional[str] = None
    hotspot_severity: Optional[str] = None
    min_overdue_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAHotspotsPublicResponse(BaseModel):
    job_id: str
    status: str
    generated_at: str
    filters: JobReviewWorkflowSLAHotspotsFiltersPublicResponse
    overdue_after_hours: int
    top_limit: int
    hotspot_count: int
    total_overdue_items: int
    max_overdue_hours: Optional[float] = None
    avg_overdue_hours: Optional[float] = None
    hotspot_kind_counts: Dict[str, int]
    hotspot_severity_counts: Dict[str, int]
    hotspot_section_counts: Dict[str, int]
    oldest_overdue: Optional[JobReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[JobReviewWorkflowSLAItemPublicResponse]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAHotspotsTrendsFiltersPublicResponse(BaseModel):
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None
    top_limit: Optional[int] = None
    hotspot_kind: Optional[str] = None
    hotspot_severity: Optional[str] = None
    min_overdue_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAHotspotsTrendsPublicResponse(BaseModel):
    job_id: str
    status: str
    generated_at: str
    filters: JobReviewWorkflowSLAHotspotsTrendsFiltersPublicResponse
    overdue_after_hours: int
    top_limit: int
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    hotspot_count_total: int = 0
    avg_hotspots_per_bucket: Optional[float] = None
    top_kind: Optional[str] = None
    top_kind_count: Optional[int] = None
    top_severity: Optional[str] = None
    top_severity_count: Optional[int] = None
    top_section: Optional[str] = None
    top_section_count: Optional[int] = None
    oldest_overdue: Optional[JobReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[JobReviewWorkflowSLAItemPublicResponse]
    total_series: list[JobReviewWorkflowSLATrendPointPublicResponse]
    severity_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    kind_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAPublicResponse(BaseModel):
    job_id: str
    status: str
    generated_at: str
    filters: JobReviewWorkflowSLAFiltersPublicResponse
    overdue_after_hours: int
    finding_total: int
    comment_total: int
    unresolved_finding_count: int
    unresolved_comment_count: int
    unresolved_total: int
    overdue_finding_count: int
    overdue_comment_count: int
    overdue_total: int
    breach_rate: Optional[float] = None
    overdue_by_severity: Dict[str, int]
    overdue_by_section: Dict[str, int]
    oldest_overdue: Optional[JobReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[JobReviewWorkflowSLAItemPublicResponse]
    workflow_summary: Dict[str, Any]

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLAProfilePublicResponse(BaseModel):
    job_id: str
    status: str
    source: str
    finding_sla_hours: Dict[str, int]
    default_comment_sla_hours: int
    saved_profile_available: bool = False
    saved_profile_valid: bool = True
    saved_profile_error: Optional[str] = None
    saved_profile_updated_at: Optional[str] = None
    saved_profile_updated_by: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobReviewWorkflowSLARecomputePublicResponse(BaseModel):
    job_id: str
    status: str
    actor: str
    recomputed_at: str
    use_saved_profile: bool = False
    applied_finding_sla_hours: Dict[str, int]
    applied_default_comment_sla_hours: int
    finding_checked_count: int
    comment_checked_count: int
    finding_updated_count: int
    comment_updated_count: int
    total_updated_count: int
    sla: JobReviewWorkflowSLAPublicResponse

    model_config = ConfigDict(extra="allow")


class CriticFindingsBulkStatusFiltersPublicResponse(BaseModel):
    apply_to_all: bool = False
    if_match_status: Optional[str] = None
    finding_status: Optional[str] = None
    severity: Optional[str] = None
    section: Optional[str] = None
    finding_ids: Optional[list[str]] = None

    model_config = ConfigDict(extra="allow")


class CriticFindingsBulkStatusPublicResponse(BaseModel):
    job_id: str
    status: str
    requested_status: str
    actor: str
    dry_run: bool = False
    persisted: bool = True
    matched_count: int
    changed_count: int
    unchanged_count: int
    not_found_finding_ids: list[str]
    filters: CriticFindingsBulkStatusFiltersPublicResponse
    updated_findings: list[CriticFatalFlawPublicResponse]

    model_config = ConfigDict(extra="allow")


class CriticRuleCheckPublicResponse(BaseModel):
    code: str
    status: str
    section: str
    detail: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class CriticFatalFlawPublicResponse(BaseModel):
    id: Optional[str] = None
    finding_id: Optional[str] = None
    code: str
    label: Optional[str] = None
    severity: str
    section: str
    status: Optional[str] = None
    version_id: Optional[str] = None
    message: str
    rationale: Optional[str] = None
    fix_suggestion: Optional[str] = None
    fix_hint: Optional[str] = None
    source: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    linked_comment_ids: Optional[list[str]] = None
    due_at: Optional[str] = None
    sla_hours: Optional[int] = None
    workflow_state: Optional[str] = None
    is_overdue: Optional[bool] = None
    age_hours: Optional[float] = None
    time_to_due_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class CriticFatalFlawStatusUpdatePublicResponse(CriticFatalFlawPublicResponse):
    dry_run: bool = False
    persisted: bool = True
    changed: bool = False

    model_config = ConfigDict(extra="allow")


class CriticFindingsListFiltersPublicResponse(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    section: Optional[str] = None
    version_id: Optional[str] = None
    workflow_state: Optional[str] = None
    include_resolved: bool = True
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class CriticFindingsListSummaryPublicResponse(BaseModel):
    finding_count: int
    open_finding_count: int
    acknowledged_finding_count: int
    resolved_finding_count: int
    pending_finding_count: int
    overdue_finding_count: int
    finding_status_counts: Dict[str, int]
    finding_severity_counts: Dict[str, int]

    model_config = ConfigDict(extra="allow")


class CriticFindingsListPublicResponse(BaseModel):
    job_id: str
    status: str
    filters: CriticFindingsListFiltersPublicResponse
    summary: CriticFindingsListSummaryPublicResponse
    findings: list[CriticFatalFlawPublicResponse]

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


class JobQualityCitationSummaryPublicResponse(BaseModel):
    citation_count: int
    architect_citation_count: int
    mel_citation_count: int
    citation_type_counts: Optional[Dict[str, int]] = None
    architect_citation_type_counts: Optional[Dict[str, int]] = None
    mel_citation_type_counts: Optional[Dict[str, int]] = None
    high_confidence_citation_count: int
    low_confidence_citation_count: int
    architect_claim_support_citation_count: int = 0
    architect_claim_support_rate: Optional[float] = None
    architect_fallback_namespace_citation_count: Optional[int] = None
    architect_fallback_namespace_citation_rate: Optional[float] = None
    mel_claim_support_citation_count: int = 0
    mel_claim_support_rate: Optional[float] = None
    mel_fallback_namespace_citation_count: Optional[int] = None
    mel_fallback_namespace_citation_rate: Optional[float] = None
    architect_rag_low_confidence_citation_count: int = 0
    mel_rag_low_confidence_citation_count: int = 0
    rag_low_confidence_citation_count: int
    fallback_namespace_citation_count: Optional[int] = None
    doc_id_present_citation_count: Optional[int] = None
    doc_id_present_citation_rate: Optional[float] = None
    retrieval_rank_present_citation_count: Optional[int] = None
    retrieval_rank_present_citation_rate: Optional[float] = None
    retrieval_confidence_present_citation_count: Optional[int] = None
    retrieval_confidence_present_citation_rate: Optional[float] = None
    retrieval_metadata_complete_citation_count: Optional[int] = None
    retrieval_metadata_complete_citation_rate: Optional[float] = None
    architect_doc_id_present_citation_count: Optional[int] = None
    architect_doc_id_present_citation_rate: Optional[float] = None
    architect_retrieval_rank_present_citation_count: Optional[int] = None
    architect_retrieval_rank_present_citation_rate: Optional[float] = None
    architect_retrieval_confidence_present_citation_count: Optional[int] = None
    architect_retrieval_confidence_present_citation_rate: Optional[float] = None
    architect_retrieval_metadata_complete_citation_count: Optional[int] = None
    architect_retrieval_metadata_complete_citation_rate: Optional[float] = None
    mel_doc_id_present_citation_count: Optional[int] = None
    mel_doc_id_present_citation_rate: Optional[float] = None
    mel_retrieval_rank_present_citation_count: Optional[int] = None
    mel_retrieval_rank_present_citation_rate: Optional[float] = None
    mel_retrieval_confidence_present_citation_count: Optional[int] = None
    mel_retrieval_confidence_present_citation_rate: Optional[float] = None
    mel_retrieval_metadata_complete_citation_count: Optional[int] = None
    mel_retrieval_metadata_complete_citation_rate: Optional[float] = None
    traceability_complete_citation_count: Optional[int] = None
    traceability_partial_citation_count: Optional[int] = None
    traceability_missing_citation_count: Optional[int] = None
    traceability_gap_citation_count: Optional[int] = None
    traceability_gap_citation_rate: Optional[float] = None
    citation_confidence_avg: Optional[float] = None
    architect_threshold_hit_rate: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobQualityCriticSummaryPublicResponse(BaseModel):
    engine: Optional[str] = None
    rule_score: Optional[float] = None
    llm_score: Optional[float] = None
    fatal_flaw_count: int
    open_finding_count: int
    acknowledged_finding_count: int
    resolved_finding_count: int
    high_severity_fatal_flaw_count: int
    medium_severity_fatal_flaw_count: int
    low_severity_fatal_flaw_count: int
    version_bindable_finding_count: Optional[int] = None
    version_bound_finding_count: Optional[int] = None
    version_binding_rate: Optional[float] = None
    rule_check_count: int
    failed_rule_check_count: int
    warned_rule_check_count: int
    llm_finding_label_counts: Optional[Dict[str, int]] = None

    model_config = ConfigDict(extra="allow")


class JobQualityArchitectSummaryPublicResponse(BaseModel):
    engine: Optional[str] = None
    llm_used: Optional[bool] = None
    retrieval_used: Optional[bool] = None
    retrieval_enabled: Optional[bool] = None
    retrieval_hits_count: Optional[int] = None
    retrieval_namespace: Optional[str] = None
    toc_schema_name: Optional[str] = None
    toc_schema_valid: Optional[bool] = None
    citation_policy: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class JobQualityArchitectClaimsSummaryPublicResponse(BaseModel):
    claim_citation_count: int = 0
    claims_total: Optional[int] = None
    key_claims_total: Optional[int] = None
    claim_paths_covered: Optional[int] = None
    key_claim_paths_covered: Optional[int] = None
    confident_claim_paths_covered: Optional[int] = None
    fallback_claim_count: Optional[int] = None
    low_confidence_claim_count: Optional[int] = None
    claim_coverage_ratio: Optional[float] = None
    key_claim_coverage_ratio: Optional[float] = None
    fallback_claim_ratio: Optional[float] = None
    threshold_hit_rate: Optional[float] = None
    traceability_complete_citation_count: Optional[int] = None
    traceability_partial_citation_count: Optional[int] = None
    traceability_missing_citation_count: Optional[int] = None
    traceability_gap_citation_count: Optional[int] = None
    traceability_complete_rate: Optional[float] = None
    traceability_gap_rate: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class JobQualityMelSummaryPublicResponse(BaseModel):
    engine: Optional[str] = None
    llm_used: Optional[bool] = None
    retrieval_used: Optional[bool] = None
    retrieval_namespace: Optional[str] = None
    retrieval_hits_count: Optional[int] = None
    avg_retrieval_confidence: Optional[float] = None
    citation_policy: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class JobQualityReadinessSummaryPublicResponse(BaseModel):
    preset_key: Optional[str] = None
    donor_id: Optional[str] = None
    expected_doc_families: list[str]
    present_doc_families: list[str]
    missing_doc_families: list[str]
    expected_count: int
    loaded_count: int
    coverage_rate: Optional[float] = None
    inventory_total_uploads: Optional[int] = None
    inventory_family_count: Optional[int] = None
    doc_family_counts: Optional[Dict[str, int]] = None
    namespace_empty: Optional[bool] = None
    low_doc_coverage: Optional[bool] = None
    architect_retrieval_enabled: Optional[bool] = None
    architect_retrieval_hits_count: Optional[int] = None
    retrieval_namespace: Optional[str] = None
    warning_count: Optional[int] = None
    warning_level: Optional[str] = None
    warnings: Optional[list[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="allow")


class JobQualityToCTextQualitySummaryPublicResponse(BaseModel):
    risk_level: str
    issues_total: int
    placeholder_finding_count: int
    repetition_finding_count: int
    placeholder_check_status: Optional[str] = None
    repetition_check_status: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobQualityExportContractPublicResponse(BaseModel):
    mode: Optional[str] = None
    status: Optional[str] = None
    passed: Optional[bool] = None
    blocking: Optional[bool] = None
    go_ahead: Optional[bool] = None
    risk_level: Optional[str] = None
    summary: Optional[str] = None
    reasons: Optional[list[str]] = None
    template_key: Optional[str] = None
    template_display_name: Optional[str] = None
    missing_required_sections: Optional[list[str]] = None
    missing_required_sheets: Optional[list[str]] = None

    model_config = ConfigDict(extra="allow")


class JobQualitySummaryPublicResponse(BaseModel):
    job_id: str
    status: str
    quality_score: Optional[float] = None
    critic_score: Optional[float] = None
    needs_revision: Optional[bool] = None
    terminal_status: Optional[str] = None
    time_to_first_draft_seconds: Optional[float] = None
    time_to_terminal_seconds: Optional[float] = None
    critic: JobQualityCriticSummaryPublicResponse
    citations: JobQualityCitationSummaryPublicResponse
    architect: JobQualityArchitectSummaryPublicResponse
    architect_claims: Optional[JobQualityArchitectClaimsSummaryPublicResponse] = None
    mel: Optional[JobQualityMelSummaryPublicResponse] = None
    mel_grounding_policy: Optional[Dict[str, Any]] = None
    grounded_gate: Optional[Dict[str, Any]] = None
    export_contract: Optional[JobQualityExportContractPublicResponse] = None
    readiness: Optional[JobQualityReadinessSummaryPublicResponse] = None
    toc_text_quality: Optional[JobQualityToCTextQualitySummaryPublicResponse] = None

    model_config = ConfigDict(extra="allow")


class JobGroundingGatePublicResponse(BaseModel):
    job_id: str
    status: str
    grounded_gate: Optional[Dict[str, Any]] = None
    preflight_grounding_policy: Optional[Dict[str, Any]] = None
    mel_grounding_policy: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    event_type: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowTimelineEventPublicResponse(ReviewWorkflowTimelineEventPublicResponse):
    job_id: Optional[str] = None
    donor_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowPublicResponse(BaseModel):
    job_count: int
    jobs_with_activity: int
    jobs_without_activity: int
    jobs_with_overdue: int
    jobs_without_overdue: int
    generated_at: str
    filters: PortfolioReviewWorkflowFiltersPublicResponse
    summary: JobReviewWorkflowSummaryPublicResponse
    top_event_type: Optional[str] = None
    top_event_type_count: Optional[int] = None
    top_donor_id: Optional[str] = None
    top_donor_event_count: Optional[int] = None
    timeline_event_type_counts: Dict[str, int]
    timeline_kind_counts: Dict[str, int]
    timeline_section_counts: Dict[str, int]
    timeline_status_counts: Dict[str, int]
    donor_event_counts: Dict[str, int]
    job_event_counts: Dict[str, int]
    latest_timeline_limit: int = 200
    latest_timeline_truncated: bool = False
    latest_timeline: list[PortfolioReviewWorkflowTimelineEventPublicResponse]

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAItemPublicResponse(JobReviewWorkflowSLAItemPublicResponse):
    job_id: Optional[str] = None
    donor_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None
    top_limit: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAPublicResponse(BaseModel):
    job_count: int
    jobs_with_overdue: int
    jobs_without_overdue: int
    generated_at: str
    filters: PortfolioReviewWorkflowSLAFiltersPublicResponse
    overdue_after_hours: int
    finding_total: int
    comment_total: int
    unresolved_finding_count: int
    unresolved_comment_count: int
    unresolved_total: int
    overdue_finding_count: int
    overdue_comment_count: int
    overdue_total: int
    breach_rate: Optional[float] = None
    overdue_by_severity: Dict[str, int]
    overdue_by_section: Dict[str, int]
    oldest_overdue: Optional[PortfolioReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[PortfolioReviewWorkflowSLAItemPublicResponse]
    top_donor_id: Optional[str] = None
    top_donor_overdue_count: Optional[int] = None
    donor_overdue_counts: Dict[str, int]
    job_overdue_counts: Dict[str, int]

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAHotspotsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None
    top_limit: Optional[int] = None
    hotspot_kind: Optional[str] = None
    hotspot_severity: Optional[str] = None
    min_overdue_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAHotspotsPublicResponse(BaseModel):
    job_count: int
    jobs_with_overdue: int
    jobs_without_overdue: int
    generated_at: str
    filters: PortfolioReviewWorkflowSLAHotspotsFiltersPublicResponse
    overdue_after_hours: int
    top_limit: int
    hotspot_count: int
    total_overdue_items: int
    max_overdue_hours: Optional[float] = None
    avg_overdue_hours: Optional[float] = None
    oldest_overdue: Optional[PortfolioReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[PortfolioReviewWorkflowSLAItemPublicResponse]
    top_donor_id: Optional[str] = None
    top_donor_overdue_count: Optional[int] = None
    donor_hotspot_counts: Dict[str, int]
    job_hotspot_counts: Dict[str, int]

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAHotspotsTrendsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None
    top_limit: Optional[int] = None
    hotspot_kind: Optional[str] = None
    hotspot_severity: Optional[str] = None
    min_overdue_hours: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLAHotspotsTrendsPublicResponse(BaseModel):
    job_count: int
    jobs_with_overdue: int
    jobs_without_overdue: int
    generated_at: str
    filters: PortfolioReviewWorkflowSLAHotspotsTrendsFiltersPublicResponse
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    hotspot_count_total: int = 0
    avg_hotspots_per_job: Optional[float] = None
    avg_hotspots_per_active_job: Optional[float] = None
    top_kind: Optional[str] = None
    top_kind_count: Optional[int] = None
    top_severity: Optional[str] = None
    top_severity_count: Optional[int] = None
    top_section: Optional[str] = None
    top_section_count: Optional[int] = None
    top_donor_id: Optional[str] = None
    top_donor_hotspot_count: Optional[int] = None
    donor_hotspot_counts: Dict[str, int]
    job_hotspot_counts: Dict[str, int]
    oldest_overdue: Optional[PortfolioReviewWorkflowSLAItemPublicResponse] = None
    top_overdue: list[PortfolioReviewWorkflowSLAItemPublicResponse]
    total_series: list[JobReviewWorkflowSLATrendPointPublicResponse]
    severity_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    kind_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    donor_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowTrendsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    event_type: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowTrendsPublicResponse(BaseModel):
    job_count: int
    jobs_with_events: int
    jobs_without_events: int
    generated_at: str
    filters: PortfolioReviewWorkflowTrendsFiltersPublicResponse
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    timeline_event_count_total: int = 0
    avg_events_per_job: Optional[float] = None
    avg_events_per_active_job: Optional[float] = None
    top_event_type: Optional[str] = None
    top_event_type_count: Optional[int] = None
    top_donor_id: Optional[str] = None
    top_donor_event_count: Optional[int] = None
    donor_event_counts: Dict[str, int]
    job_event_counts: Dict[str, int]
    total_series: list[JobReviewWorkflowTrendPointPublicResponse]
    event_type_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    kind_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    status_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]
    donor_series: Dict[str, list[JobReviewWorkflowTrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLATrendsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    toc_text_risk_level: Optional[str] = None
    finding_id: Optional[str] = None
    finding_code: Optional[str] = None
    finding_section: Optional[str] = None
    comment_status: Optional[str] = None
    workflow_state: Optional[str] = None
    overdue_after_hours: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class PortfolioReviewWorkflowSLATrendsPublicResponse(BaseModel):
    job_count: int
    jobs_with_overdue: int
    jobs_without_overdue: int
    generated_at: str
    filters: PortfolioReviewWorkflowSLATrendsFiltersPublicResponse
    bucket_granularity: str = "day"
    bucket_count: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    overdue_finding_count: int = 0
    overdue_comment_count: int = 0
    overdue_total: int = 0
    unresolved_total: int = 0
    breach_rate: Optional[float] = None
    avg_overdue_per_job: Optional[float] = None
    avg_overdue_per_active_job: Optional[float] = None
    top_severity: Optional[str] = None
    top_severity_count: Optional[int] = None
    top_section: Optional[str] = None
    top_section_count: Optional[int] = None
    top_donor_id: Optional[str] = None
    top_donor_overdue_count: Optional[int] = None
    donor_overdue_counts: Dict[str, int]
    job_overdue_counts: Dict[str, int]
    total_series: list[JobReviewWorkflowSLATrendPointPublicResponse]
    severity_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    section_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]
    donor_series: Dict[str, list[JobReviewWorkflowSLATrendPointPublicResponse]]

    model_config = ConfigDict(extra="allow")


class PortfolioMetricsFiltersPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    status: Optional[str] = None
    hitl_enabled: Optional[bool] = None
    warning_level: Optional[str] = None
    grounding_risk_level: Optional[str] = None
    finding_status: Optional[str] = None
    finding_severity: Optional[str] = None
    toc_text_risk_level: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PortfolioMetricsPublicResponse(BaseModel):
    job_count: int
    filters: PortfolioMetricsFiltersPublicResponse
    status_counts: Dict[str, int]
    donor_counts: Dict[str, int]
    warning_level_counts: Dict[str, int]
    warning_level_job_counts: Dict[str, int]
    warning_level_job_rates: Dict[str, Optional[float]]
    grounding_risk_counts: Dict[str, int]
    grounding_risk_job_counts: Dict[str, int]
    grounding_risk_job_rates: Dict[str, Optional[float]]
    grounding_risk_high_job_count: int
    grounding_risk_medium_job_count: int
    grounding_risk_low_job_count: int
    grounding_risk_unknown_job_count: int
    terminal_job_count: int
    hitl_job_count: int
    total_pause_count: int
    total_resume_count: int
    avg_time_to_first_draft_seconds: Optional[float] = None
    avg_time_to_terminal_seconds: Optional[float] = None
    avg_time_in_pending_hitl_seconds: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class PortfolioQualityCriticSummaryPublicResponse(BaseModel):
    open_findings_total: int
    open_findings_per_job_avg: Optional[float] = None
    high_severity_findings_total: int
    fatal_flaws_total: int
    needs_revision_job_count: int
    needs_revision_rate: Optional[float] = None
    llm_finding_label_counts: Optional[Dict[str, int]] = None
    llm_advisory_diagnostics_job_count: Optional[int] = None
    llm_advisory_applied_job_count: Optional[int] = None
    llm_advisory_applied_rate: Optional[float] = None
    llm_advisory_candidate_finding_count: Optional[int] = None
    llm_advisory_rejected_reason_counts: Optional[Dict[str, int]] = None

    model_config = ConfigDict(extra="allow")


class PortfolioQualityCitationSummaryPublicResponse(BaseModel):
    citation_count_total: int
    architect_citation_count_total: int = 0
    architect_claim_support_citation_count: int = 0
    architect_claim_support_rate: Optional[float] = None
    citation_confidence_avg: Optional[float] = None
    citation_type_counts_total: Optional[Dict[str, int]] = None
    architect_citation_type_counts_total: Optional[Dict[str, int]] = None
    mel_citation_type_counts_total: Optional[Dict[str, int]] = None
    low_confidence_citation_count: int
    low_confidence_citation_rate: Optional[float] = None
    architect_rag_low_confidence_citation_count: int = 0
    architect_rag_low_confidence_citation_rate: Optional[float] = None
    mel_rag_low_confidence_citation_count: int = 0
    mel_rag_low_confidence_citation_rate: Optional[float] = None
    rag_low_confidence_citation_count: int
    rag_low_confidence_citation_rate: Optional[float] = None
    fallback_namespace_citation_count: Optional[int] = None
    fallback_namespace_citation_rate: Optional[float] = None
    doc_id_present_citation_count: Optional[int] = None
    doc_id_present_citation_rate: Optional[float] = None
    retrieval_rank_present_citation_count: Optional[int] = None
    retrieval_rank_present_citation_rate: Optional[float] = None
    retrieval_confidence_present_citation_count: Optional[int] = None
    retrieval_confidence_present_citation_rate: Optional[float] = None
    retrieval_metadata_complete_citation_count: Optional[int] = None
    retrieval_metadata_complete_citation_rate: Optional[float] = None
    architect_doc_id_present_citation_count: Optional[int] = None
    architect_doc_id_present_citation_rate: Optional[float] = None
    architect_retrieval_rank_present_citation_count: Optional[int] = None
    architect_retrieval_rank_present_citation_rate: Optional[float] = None
    architect_retrieval_confidence_present_citation_count: Optional[int] = None
    architect_retrieval_confidence_present_citation_rate: Optional[float] = None
    architect_retrieval_metadata_complete_citation_count: Optional[int] = None
    architect_retrieval_metadata_complete_citation_rate: Optional[float] = None
    mel_doc_id_present_citation_count: Optional[int] = None
    mel_doc_id_present_citation_rate: Optional[float] = None
    mel_retrieval_rank_present_citation_count: Optional[int] = None
    mel_retrieval_rank_present_citation_rate: Optional[float] = None
    mel_retrieval_confidence_present_citation_count: Optional[int] = None
    mel_retrieval_confidence_present_citation_rate: Optional[float] = None
    mel_retrieval_metadata_complete_citation_count: Optional[int] = None
    mel_retrieval_metadata_complete_citation_rate: Optional[float] = None
    traceability_complete_citation_count: Optional[int] = None
    traceability_complete_citation_rate: Optional[float] = None
    traceability_partial_citation_count: Optional[int] = None
    traceability_partial_citation_rate: Optional[float] = None
    traceability_missing_citation_count: Optional[int] = None
    traceability_missing_citation_rate: Optional[float] = None
    traceability_gap_citation_count: Optional[int] = None
    traceability_gap_citation_rate: Optional[float] = None
    architect_threshold_hit_rate_avg: Optional[float] = None
    architect_claim_support_rate_avg: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class PortfolioQualityWeightedSignalPublicResponse(BaseModel):
    count: int
    weight: int
    weighted_score: int

    model_config = ConfigDict(extra="allow")


class PortfolioQualityToCTextQualitySummaryPublicResponse(BaseModel):
    issues_total: int
    placeholder_finding_count: int
    repetition_finding_count: int
    risk_counts: Dict[str, int]
    risk_job_rates: Dict[str, Optional[float]]
    high_risk_job_count: int
    medium_risk_job_count: int
    low_risk_job_count: int
    unknown_risk_job_count: int
    high_risk_job_rate: Optional[float] = None
    placeholder_check_status_counts: Dict[str, int]
    repetition_check_status_counts: Dict[str, int]

    model_config = ConfigDict(extra="allow")


class PortfolioQualityDonorWeightedRiskPublicResponse(BaseModel):
    weighted_score: int
    high_priority_signal_count: int
    open_findings_total: int
    high_severity_findings_total: int
    needs_revision_job_count: int
    architect_citation_count_total: int = 0
    architect_claim_support_citation_count: int = 0
    architect_claim_support_rate: Optional[float] = None
    low_confidence_citation_count: int
    rag_low_confidence_citation_count: int
    architect_rag_low_confidence_citation_count: int = 0
    mel_rag_low_confidence_citation_count: int = 0
    citation_type_counts: Optional[Dict[str, int]] = None
    architect_citation_type_counts: Optional[Dict[str, int]] = None
    mel_citation_type_counts: Optional[Dict[str, int]] = None
    fallback_namespace_citation_count: Optional[int] = None
    doc_id_present_citation_count: Optional[int] = None
    doc_id_present_citation_rate: Optional[float] = None
    retrieval_rank_present_citation_count: Optional[int] = None
    retrieval_rank_present_citation_rate: Optional[float] = None
    retrieval_confidence_present_citation_count: Optional[int] = None
    retrieval_confidence_present_citation_rate: Optional[float] = None
    retrieval_metadata_complete_citation_count: Optional[int] = None
    retrieval_metadata_complete_citation_rate: Optional[float] = None
    architect_doc_id_present_citation_count: Optional[int] = None
    architect_doc_id_present_citation_rate: Optional[float] = None
    architect_retrieval_rank_present_citation_count: Optional[int] = None
    architect_retrieval_rank_present_citation_rate: Optional[float] = None
    architect_retrieval_confidence_present_citation_count: Optional[int] = None
    architect_retrieval_confidence_present_citation_rate: Optional[float] = None
    architect_retrieval_metadata_complete_citation_count: Optional[int] = None
    architect_retrieval_metadata_complete_citation_rate: Optional[float] = None
    mel_doc_id_present_citation_count: Optional[int] = None
    mel_doc_id_present_citation_rate: Optional[float] = None
    mel_retrieval_rank_present_citation_count: Optional[int] = None
    mel_retrieval_rank_present_citation_rate: Optional[float] = None
    mel_retrieval_confidence_present_citation_count: Optional[int] = None
    mel_retrieval_confidence_present_citation_rate: Optional[float] = None
    mel_retrieval_metadata_complete_citation_count: Optional[int] = None
    mel_retrieval_metadata_complete_citation_rate: Optional[float] = None
    traceability_complete_citation_count: Optional[int] = None
    traceability_partial_citation_count: Optional[int] = None
    traceability_missing_citation_count: Optional[int] = None
    traceability_gap_citation_count: Optional[int] = None
    llm_finding_label_counts: Optional[Dict[str, int]] = None
    llm_advisory_applied_label_counts: Optional[Dict[str, int]] = None
    llm_advisory_rejected_label_counts: Optional[Dict[str, int]] = None
    llm_advisory_diagnostics_job_count: Optional[int] = None
    llm_advisory_applied_job_count: Optional[int] = None
    llm_advisory_applied_rate: Optional[float] = None
    llm_advisory_candidate_finding_count: Optional[int] = None
    llm_advisory_rejected_reason_counts: Optional[Dict[str, int]] = None

    model_config = ConfigDict(extra="allow")


class PortfolioQualityDonorGroundedGatePublicResponse(BaseModel):
    job_count: int
    present_job_count: int
    blocked_job_count: int
    passed_job_count: int
    block_rate: Optional[float] = None
    block_rate_among_present: Optional[float] = None
    pass_rate_among_present: Optional[float] = None
    section_fail_counts: Dict[str, int]
    reason_counts: Dict[str, int]

    model_config = ConfigDict(extra="allow")


class PortfolioQualityPublicResponse(BaseModel):
    job_count: int
    filters: PortfolioMetricsFiltersPublicResponse
    status_counts: Dict[str, int]
    donor_counts: Dict[str, int]
    terminal_job_count: int
    quality_score_job_count: int
    critic_score_job_count: int
    avg_quality_score: Optional[float] = None
    avg_critic_score: Optional[float] = None
    severity_weighted_risk_score: int
    high_priority_signal_count: int
    critic: PortfolioQualityCriticSummaryPublicResponse
    citations: PortfolioQualityCitationSummaryPublicResponse
    priority_signal_breakdown: Dict[str, PortfolioQualityWeightedSignalPublicResponse]
    donor_weighted_risk_breakdown: Dict[str, PortfolioQualityDonorWeightedRiskPublicResponse]
    grounded_gate_present_job_count: int
    grounded_gate_blocked_job_count: int
    grounded_gate_passed_job_count: int
    grounded_gate_block_rate: Optional[float] = None
    grounded_gate_block_rate_among_present: Optional[float] = None
    grounded_gate_pass_rate_among_present: Optional[float] = None
    grounded_gate_section_fail_counts: Dict[str, int]
    grounded_gate_reason_counts: Dict[str, int]
    donor_grounded_gate_breakdown: Dict[str, PortfolioQualityDonorGroundedGatePublicResponse]
    toc_text_quality: PortfolioQualityToCTextQualitySummaryPublicResponse
    donor_needs_revision_counts: Dict[str, int]
    donor_open_findings_counts: Dict[str, int]

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


class JobHITLHistoryFiltersPublicResponse(BaseModel):
    event_type: Optional[str] = None
    checkpoint_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobHITLHistoryEventPublicResponse(BaseModel):
    event_id: Optional[str] = None
    ts: Optional[str] = None
    type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    status: Optional[str] = None
    checkpoint_id: Optional[str] = None
    checkpoint_stage: Optional[str] = None
    checkpoint_status: Optional[str] = None
    resuming_from: Optional[str] = None
    approved: Optional[bool] = None
    feedback: Optional[str] = None
    actor: Optional[str] = None
    request_id: Optional[str] = None
    reason: Optional[str] = None
    backend: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class JobHITLHistoryPublicResponse(BaseModel):
    job_id: str
    status: str
    filters: JobHITLHistoryFiltersPublicResponse
    event_count: int
    event_type_counts: Dict[str, int]
    events: list[JobHITLHistoryEventPublicResponse]

    model_config = ConfigDict(extra="allow")


class IngestRecentRecordPublicResponse(BaseModel):
    event_id: str
    ts: str
    donor_id: str
    tenant_id: Optional[str] = None
    namespace: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class IngestRecentListPublicResponse(BaseModel):
    count: int
    donor_id: Optional[str] = None
    tenant_id: Optional[str] = None
    records: list[IngestRecentRecordPublicResponse]

    model_config = ConfigDict(extra="allow")


class IngestInventoryDocFamilyPublicResponse(BaseModel):
    tenant_id: Optional[str] = None
    donor_id: str
    doc_family: str
    count: int
    latest_ts: Optional[str] = None
    latest_filename: Optional[str] = None
    latest_event_id: Optional[str] = None
    latest_source_type: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class IngestInventoryPublicResponse(BaseModel):
    donor_id: Optional[str] = None
    tenant_id: Optional[str] = None
    total_uploads: int
    family_count: int
    doc_family_counts: Dict[str, int]
    doc_families: list[IngestInventoryDocFamilyPublicResponse]

    model_config = ConfigDict(extra="allow")


class GeneratePreflightWarningPublicResponse(BaseModel):
    code: str
    severity: str
    message: str

    model_config = ConfigDict(extra="allow")


class GeneratePreflightArchitectClaimsPublicResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    claim_citation_count: Optional[int] = None
    key_claim_coverage_ratio: Optional[float] = None
    fallback_claim_ratio: Optional[float] = None
    threshold_hit_rate: Optional[float] = None
    traceability_complete_citation_count: Optional[int] = None
    traceability_partial_citation_count: Optional[int] = None
    traceability_missing_citation_count: Optional[int] = None
    traceability_gap_citation_count: Optional[int] = None
    traceability_gap_rate: Optional[float] = None
    retrieval_hits_count: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class GeneratePreflightGroundingPolicyPublicResponse(BaseModel):
    mode: str
    risk_level: str
    reasons: list[str]
    summary: str
    blocking: bool
    go_ahead: bool
    thresholds: Dict[str, Any]
    architect_claims: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class GeneratePreflightPublicResponse(BaseModel):
    donor_id: str
    tenant_id: Optional[str] = None
    retrieval_namespace: Optional[str] = None
    retrieval_namespace_normalized: Optional[str] = None
    retrieval_query_terms: list[str]
    expected_doc_families: list[str]
    present_doc_families: list[str]
    missing_doc_families: list[str]
    doc_family_min_uploads: Dict[str, int]
    depth_ready_doc_families: list[str]
    depth_gap_doc_families: list[str]
    expected_count: int
    loaded_count: int
    coverage_rate: Optional[float] = None
    depth_ready_count: int
    depth_gap_count: int
    depth_coverage_rate: Optional[float] = None
    inventory_total_uploads: int
    inventory_family_count: int
    namespace_empty: bool
    warning_count: int
    warning_level: str
    risk_level: str
    grounding_risk_level: str
    grounding_policy: Optional[GeneratePreflightGroundingPolicyPublicResponse] = None
    architect_claims: Optional[GeneratePreflightArchitectClaimsPublicResponse] = None
    go_ahead: bool
    warnings: list[GeneratePreflightWarningPublicResponse]

    model_config = ConfigDict(extra="allow")


class QueueWorkerHeartbeatPolicyPublicResponse(BaseModel):
    mode: str

    model_config = ConfigDict(extra="allow")


class QueueWorkerHeartbeatStatusPublicResponse(BaseModel):
    key: Optional[str] = None
    ttl_seconds: Optional[float] = None
    present: bool
    healthy: bool
    age_seconds: Optional[float] = None
    source: Optional[str] = None
    error: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class QueueWorkerHeartbeatPublicResponse(BaseModel):
    mode: str
    policy: QueueWorkerHeartbeatPolicyPublicResponse
    consumer_enabled: bool
    heartbeat: QueueWorkerHeartbeatStatusPublicResponse

    model_config = ConfigDict(extra="allow")


class DeadLetterQueueItemPublicResponse(BaseModel):
    index: int
    dispatch_id: Optional[str] = None
    task_name: Optional[str] = None
    job_id: Optional[str] = None
    reason: Optional[str] = None
    attempt: Optional[int] = None
    max_attempts: Optional[int] = None
    queued_at: Optional[float] = None
    first_failed_at: Optional[float] = None
    failed_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    raw_payload: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DeadLetterQueueListPublicResponse(BaseModel):
    mode: str
    queue_name: str
    dead_letter_queue_name: str
    dead_letter_queue_size: int
    items: list[DeadLetterQueueItemPublicResponse]

    model_config = ConfigDict(extra="allow")


class DeadLetterQueueMutationPublicResponse(BaseModel):
    mode: str
    queue_name: str
    dead_letter_queue_name: str
    requested_count: int
    affected_count: int
    dead_letter_queue_size: int
    skipped_count: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class IngestPresetChecklistItemPublicResponse(BaseModel):
    id: str
    label: str
    source_type: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class IngestPresetSummaryPublicResponse(BaseModel):
    preset_key: str
    donor_id: Optional[str] = None
    title: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class IngestPresetListPublicResponse(BaseModel):
    presets: list[IngestPresetSummaryPublicResponse]

    model_config = ConfigDict(extra="allow")


class IngestPresetDetailPublicResponse(BaseModel):
    preset_key: str
    donor_id: Optional[str] = None
    title: Optional[str] = None
    metadata: Dict[str, Any]
    checklist_items: list[IngestPresetChecklistItemPublicResponse]
    recommended_docs: list[str]

    model_config = ConfigDict(extra="allow")


class RBMSamplePresetSummaryPublicResponse(BaseModel):
    sample_id: str
    donor_id: Optional[str] = None
    title: Optional[str] = None
    country: Optional[str] = None
    timeframe: Optional[str] = None
    source_file: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class RBMSamplePresetListPublicResponse(BaseModel):
    presets: list[RBMSamplePresetSummaryPublicResponse]

    model_config = ConfigDict(extra="allow")


class RBMSamplePresetDetailPublicResponse(BaseModel):
    sample_id: str
    source_file: Optional[str] = None
    payload: Dict[str, Any]
    generate_payload: Dict[str, Any]

    model_config = ConfigDict(extra="allow")
