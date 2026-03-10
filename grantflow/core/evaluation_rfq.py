from __future__ import annotations

from typing import Any, Dict, Iterable, Literal

from pydantic import BaseModel, Field


EVALUATION_RFQ_PROPOSAL_MODE = "evaluation_rfq"
KATCH_EVALUATION_RFQ_PROFILE = "katch_final_assessment"


class EvaluationMethodComponent(BaseModel):
    method: str = Field(description="Named data collection or analysis method")
    purpose: str = Field(description="Why this method is used in the evaluation design")
    respondent_group: str = Field(description="Primary respondent or evidence group")
    evidence_source: str = Field(description="Primary source or artifact used for this method")


class EvaluationTeamRole(BaseModel):
    role: str = Field(description="Evaluation team role")
    responsibility: str = Field(description="Main responsibility for this role")


class EvaluationKeyPersonnel(BaseModel):
    name: str = Field(description="Named staff member or placeholder personnel label")
    role: str = Field(description="Assigned role in the proposal team")
    qualifications: str = Field(description="Short qualification summary relevant to the assignment")
    level_of_effort: str = Field(description="Indicative level of effort or staffing contribution")
    cv_status: str = Field(description="CV attachment status: ready|pending|partial")


class EvaluationDeliverable(BaseModel):
    deliverable: str = Field(description="Deliverable name")
    timing: str = Field(description="Timing or milestone window")
    purpose: str = Field(description="Why the deliverable matters for the assignment")


class EvaluationComplianceItem(BaseModel):
    requirement: str = Field(description="Named RFQ requirement or attachment expectation")
    response_section: str = Field(description="Where the response covers this requirement")
    evidence: str = Field(description="What evidence or attachment supports compliance")
    status: str = Field(description="Compliance status: ready|partial|pending")
    notes: str = Field(default="", description="Short implementation or packaging note")


class EvaluationCostItem(BaseModel):
    cost_bucket: str = Field(description="Named cost bucket")
    basis: str = Field(description="What drives the cost bucket")
    estimate: str = Field(description="Indicative estimate or pricing note")
    notes: str = Field(default="", description="Short pricing or packaging note")


class EvaluationSubmissionItem(BaseModel):
    artifact: str = Field(description="Named file or package artifact required for submission")
    owner: str = Field(description="Responsible owner for the artifact")
    status: str = Field(description="Packaging status: ready|partial|pending")
    notes: str = Field(default="", description="Short note on completeness or remaining action")


class EvaluationRFQTOC(BaseModel):
    proposal_mode: Literal["evaluation_rfq"] = EVALUATION_RFQ_PROPOSAL_MODE
    rfq_profile: str | None = Field(default=None, description="Optional RFQ-specific contract profile")
    brief: str = Field(description="Short summary of the technical response")
    background_context: str = Field(description="Relevant project and assignment context")
    evaluation_purpose: str = Field(description="Purpose of the evaluation assignment")
    evaluation_questions: list[str] = Field(default_factory=list)
    methodology_overview: str = Field(description="Overall evaluation design and approach")
    methodology_components: list[EvaluationMethodComponent] = Field(default_factory=list)
    team_composition: list[EvaluationTeamRole] = Field(default_factory=list)
    key_personnel: list[EvaluationKeyPersonnel] = Field(default_factory=list)
    deliverables: list[EvaluationDeliverable] = Field(default_factory=list)
    workplan_summary: list[str] = Field(default_factory=list)
    assumptions_risks: list[str] = Field(default_factory=list)
    organization_information: str = Field(default="", description="Organization information and legal status summary")
    technical_approach_summary: str = Field(default="", description="Technical approach and methodology narrative")
    sampling_plan: str = Field(default="", description="Sampling and respondent selection summary")
    analytical_software: list[str] = Field(default_factory=list, description="Software or analytical tools to be used")
    ethical_considerations: list[str] = Field(default_factory=list, description="Do-no-harm, consent, and confidentiality safeguards")
    level_of_effort_summary: str = Field(default="", description="Activity-based level of effort summary")
    technical_experience_summary: str = Field(default="", description="Past performance and technical experience summary")
    sample_outputs_summary: str = Field(default="", description="Referenced sample outputs or report evidence")
    annex_readiness: list[str] = Field(default_factory=list, description="Annexes or required supporting attachments expected for submission")
    compliance_matrix: list[EvaluationComplianceItem] = Field(
        default_factory=list,
        description="RFQ compliance matrix mapping requirements to response sections and supporting evidence",
    )
    financial_summary: str = Field(default="", description="Short financial proposal companion summary for the technical package")
    cost_structure: list[EvaluationCostItem] = Field(default_factory=list)
    pricing_assumptions: list[str] = Field(default_factory=list)
    payment_schedule_summary: str = Field(default="", description="Milestone-based payment or invoicing summary")
    submission_package_checklist: list[EvaluationSubmissionItem] = Field(default_factory=list)


def is_evaluation_rfq_mode(input_context: Dict[str, Any] | None) -> bool:
    ctx = input_context if isinstance(input_context, dict) else {}
    return str(ctx.get("proposal_mode") or "").strip().lower() == EVALUATION_RFQ_PROPOSAL_MODE


def evaluation_rfq_schema() -> type[EvaluationRFQTOC]:
    return EvaluationRFQTOC


def evaluation_rfq_profile(input_context: Dict[str, Any] | None) -> str:
    ctx = input_context if isinstance(input_context, dict) else {}
    return str(ctx.get("rfq_profile") or "").strip().lower()


def is_katch_evaluation_rfq(input_context: Dict[str, Any] | None) -> bool:
    return is_evaluation_rfq_mode(input_context) and evaluation_rfq_profile(input_context) == KATCH_EVALUATION_RFQ_PROFILE


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _rfq_methods(input_context: Dict[str, Any]) -> list[str]:
    methods = input_context.get("methods") or input_context.get("evaluation_methods") or []
    if isinstance(methods, list):
        return [text for item in methods if (text := _clean_text(item))]
    if isinstance(methods, str):
        return [text for chunk in methods.split(",") if (text := _clean_text(chunk))]
    return []


def _rfq_deliverables(input_context: Dict[str, Any]) -> list[str]:
    deliverables = input_context.get("deliverables") or input_context.get("expected_deliverables") or []
    if isinstance(deliverables, list):
        return [text for item in deliverables if (text := _clean_text(item))]
    if isinstance(deliverables, str):
        return [text for chunk in deliverables.split(",") if (text := _clean_text(chunk))]
    return []


def _rfq_questions(input_context: Dict[str, Any]) -> list[str]:
    questions = input_context.get("evaluation_questions") or input_context.get("key_questions") or []
    if isinstance(questions, list):
        return [text for item in questions if (text := _clean_text(item))]
    return []


def _build_method_components(methods: Iterable[str], *, project: str, country: str) -> list[Dict[str, str]]:
    components: list[Dict[str, str]] = []
    for method in methods:
        lowered = method.lower()
        if "outcome harvesting" in lowered:
            components.append(
                {
                    "method": "Outcome Harvesting",
                    "purpose": f"Capture substantiated outcome-level changes linked to {project} implementation in {country}.",
                    "respondent_group": "Project stakeholders, local partners, and implementation leadership",
                    "evidence_source": "Outcome stories, validation interviews, and supporting project records",
                }
            )
        elif "social media" in lowered:
            components.append(
                {
                    "method": "Social Media Analysis",
                    "purpose": "Assess public-facing communication reach, narrative shifts, and engagement patterns.",
                    "respondent_group": "Digital audiences and project communication channels",
                    "evidence_source": "Platform analytics, content samples, and coded engagement trends",
                }
            )
        elif "focus group" in lowered:
            components.append(
                {
                    "method": "Focus Group Discussions",
                    "purpose": "Test beneficiary and stakeholder perceptions against documented implementation results.",
                    "respondent_group": "Beneficiaries, community stakeholders, and partner representatives",
                    "evidence_source": "FGD guides, notes, transcripts, and coded synthesis summaries",
                }
            )
        elif "survey" in lowered:
            components.append(
                {
                    "method": "Beneficiary Survey",
                    "purpose": "Quantify beneficiary experience and triangulate outcome-level findings.",
                    "respondent_group": "Target beneficiaries and end users",
                    "evidence_source": "Structured survey instrument, response dataset, and cleaning log",
                }
            )
        else:
            components.append(
                {
                    "method": method,
                    "purpose": f"Generate decision-useful evidence for the {project} performance evaluation.",
                    "respondent_group": "Priority stakeholder groups defined in the inception phase",
                    "evidence_source": "Validated primary and secondary evidence for the evaluation file",
                }
            )
    return components


def _build_team_roles(project: str) -> list[Dict[str, str]]:
    return [
        {
            "role": "Team Lead / Evaluation Director",
            "responsibility": f"Lead technical design, quality assurance, and client communication for the {project} evaluation.",
        },
        {
            "role": "MEL / Evaluation Specialist",
            "responsibility": "Own evaluation matrix, data quality logic, and triangulation of qualitative and quantitative evidence.",
        },
        {
            "role": "Field Research Coordinator",
            "responsibility": "Manage respondent scheduling, field protocols, consent, and secure data collection logistics.",
        },
    ]


def _build_key_personnel(project: str) -> list[Dict[str, str]]:
    return [
        {
            "name": "Proposed Team Lead",
            "role": "Team Lead / Evaluation Director",
            "qualifications": f"Senior evaluation lead with relevant final-assessment and donor-reporting experience for the {project} assignment.",
            "level_of_effort": "Lead oversight across inception, fieldwork, analysis, and final reporting",
            "cv_status": "ready",
        },
        {
            "name": "Proposed MEL Specialist",
            "role": "MEL / Evaluation Specialist",
            "qualifications": "Mixed-methods evaluation specialist with indicator, survey, and triangulation experience.",
            "level_of_effort": "Core technical support for evaluation matrix, tools, and analytical synthesis",
            "cv_status": "ready",
        },
        {
            "name": "Proposed Field Coordinator",
            "role": "Field Research Coordinator",
            "qualifications": "Fieldwork and respondent-management lead with secure data collection and consent protocol experience.",
            "level_of_effort": "Field logistics, scheduling, respondent access, and data collection quality control",
            "cv_status": "ready",
        },
    ]


def _build_deliverable_rows(deliverables: Iterable[str]) -> list[Dict[str, str]]:
    rows: list[Dict[str, str]] = []
    for raw in deliverables:
        lowered = raw.lower()
        if "inception" in lowered:
            rows.append(
                {
                    "deliverable": "Inception Report, Evaluation Design, and Work Plan",
                    "timing": "Mobilization phase",
                    "purpose": "Confirm evaluation questions, methodology, sampling logic, and delivery calendar.",
                }
            )
        elif "bi-week" in lowered or "update" in lowered:
            rows.append(
                {
                    "deliverable": "Bi-Weekly Progress Updates",
                    "timing": "Fieldwork and analysis phase",
                    "purpose": "Keep the client aligned on progress, risks, and required decisions.",
                }
            )
        elif "workshop" in lowered or "event" in lowered:
            rows.append(
                {
                    "deliverable": "Validation Workshop / Virtual Debrief",
                    "timing": "Post-analysis validation stage",
                    "purpose": "Test preliminary findings with stakeholders before report finalization.",
                }
            )
        elif "draft" in lowered:
            rows.append(
                {
                    "deliverable": "Draft Evaluation Report",
                    "timing": "Analysis closeout",
                    "purpose": "Present evidence-backed findings, conclusions, and recommendations for review.",
                }
            )
        elif "brief" in lowered:
            rows.append(
                {
                    "deliverable": "Stand-alone Brief",
                    "timing": "Reporting closeout",
                    "purpose": "Provide an executive-ready summary of findings and recommendations.",
                }
            )
        elif "final" in lowered:
            rows.append(
                {
                    "deliverable": "Final Evaluation Report",
                    "timing": "Final submission",
                    "purpose": "Submit the finalized evidence package after client review and quality assurance.",
                }
            )
        else:
            rows.append(
                {
                    "deliverable": raw,
                    "timing": "Assignment workplan",
                    "purpose": "Meet the contractual reporting and quality requirements of the RFQ.",
                }
            )
    return rows


def _build_katch_deliverable_rows(deliverables: Iterable[str]) -> list[Dict[str, str]]:
    rows = _build_deliverable_rows(deliverables)
    if rows:
        return rows
    return [
        {
            "deliverable": "Draft Inception Report with Evaluation Design and Work Plan",
            "timing": "July 14, 2025",
            "purpose": "Submit the first complete evaluation design, work plan, and data collection architecture for review.",
        },
        {
            "deliverable": "Final Inception Report with Evaluation Design and Work Plan",
            "timing": "July 28, 2025",
            "purpose": "Lock the approved design, methods, timeline, and reporting structure before fieldwork.",
        },
        {
            "deliverable": "Report on Field Survey Data Collection / Draft Evaluation Report",
            "timing": "September 15, 2025",
            "purpose": "Document fieldwork completion and present draft findings for Winrock and USDOS review.",
        },
        {
            "deliverable": "Virtual Event / Workshop",
            "timing": "September 15, 2025",
            "purpose": "Validate key findings and recommendations with project stakeholders before finalization.",
        },
        {
            "deliverable": "Final Evaluation Report and Stand-alone Brief",
            "timing": "September 30, 2025",
            "purpose": "Submit the final evidence-backed evaluation package and concise external-facing brief.",
        },
    ]


def _build_katch_compliance_matrix() -> list[Dict[str, str]]:
    return [
        {
            "requirement": "Organization information and legal status package",
            "response_section": "Organization Information",
            "evidence": "Registration certificate, legal business name, audited financial statement",
            "status": "ready",
            "notes": "Package with legal status and operating profile should be attached with the technical response.",
        },
        {
            "requirement": "Technical approach and evaluation methodology",
            "response_section": "Analysis and Proposed Approaches / Methodologies",
            "evidence": "Method narrative, document review plan, analysis approach, risk/limitation note",
            "status": "ready",
            "notes": "Response must explain how methods answer the evaluation purpose and questions.",
        },
        {
            "requirement": "Sampling and respondent coverage",
            "response_section": "Sampling Plan",
            "evidence": "Stakeholder groups, beneficiary sample logic, field coverage assumptions",
            "status": "ready",
            "notes": "Sampling should cover KATCH staff, authorities, partners, and beneficiary groups.",
        },
        {
            "requirement": "Personnel and team composition",
            "response_section": "Personnel and Team Composition",
            "evidence": "Named roles, responsibilities, CV annexes",
            "status": "ready",
            "notes": "Reviewer should be able to see clear delivery ownership by role.",
        },
        {
            "requirement": "Activity-based work plan and level of effort",
            "response_section": "Workplan & Deliverables / Proposed Level of Effort",
            "evidence": "Work plan summary, Gantt-style timeline, LOE matrix",
            "status": "ready",
            "notes": "Package should show timing and person-days by phase and role.",
        },
        {
            "requirement": "Past performance references and sample outputs",
            "response_section": "Technical Experience and Past Performance References / Sample Technical Outputs",
            "evidence": "Comparable assignments, client references, sample reports or briefs",
            "status": "ready",
            "notes": "At least one comparable technical output should be identified for reviewer validation.",
        },
        {
            "requirement": "Annexes and supporting attachments",
            "response_section": "Annex Readiness",
            "evidence": "CVs, work plan, LOE matrix, sample output, registration/audit evidence",
            "status": "ready",
            "notes": "All named annexes should be packaged with the technical proposal before submission.",
        },
    ]


def _build_katch_cost_structure() -> list[Dict[str, str]]:
    return [
        {
            "cost_bucket": "Professional fees",
            "basis": "Person-days by role across inception, fieldwork, analysis, workshop, and reporting",
            "estimate": "Rate card and level-of-effort matrix aligned to the work plan",
            "notes": "Should reconcile to team composition and proposed LOE.",
        },
        {
            "cost_bucket": "Fieldwork and travel",
            "basis": "Field visits, local transport, accommodation, and respondent-access logistics",
            "estimate": "Activity-based fieldwork budget with travel assumptions",
            "notes": "State whether costs are estimated or fixed by location and duration.",
        },
        {
            "cost_bucket": "Data collection and analysis",
            "basis": "Survey administration, transcription, translation, coding, and analytical tooling",
            "estimate": "Method-linked cost note tied to the evaluation design",
            "notes": "Should align with methodology components and software plan.",
        },
        {
            "cost_bucket": "Workshops and reporting",
            "basis": "Validation workshop, presentation materials, final report production, and brief formatting",
            "estimate": "Milestone-based reporting and dissemination cost note",
            "notes": "Tie payment timing to deliverable acceptance where possible.",
        },
    ]


def _build_katch_submission_package_checklist() -> list[Dict[str, str]]:
    return [
        {
            "artifact": "Technical proposal narrative",
            "owner": "Proposal manager",
            "status": "ready",
            "notes": "Final export-ready technical response with methodology, staffing, and deliverables sections.",
        },
        {
            "artifact": "Financial proposal companion",
            "owner": "Finance / proposal manager",
            "status": "ready",
            "notes": "Separate pricing note aligned to LOE, fieldwork, analysis, and reporting structure.",
        },
        {
            "artifact": "CV annex package",
            "owner": "Team lead / HR support",
            "status": "ready",
            "notes": "CVs for key personnel aligned to the key personnel table.",
        },
        {
            "artifact": "Sample technical outputs",
            "owner": "Proposal manager",
            "status": "ready",
            "notes": "Comparable final evaluation reports or briefs referenced in the technical response.",
        },
        {
            "artifact": "Work plan and level-of-effort annexes",
            "owner": "Evaluation lead",
            "status": "ready",
            "notes": "Gantt-style work plan and LOE matrix aligned to deliverables and staffing.",
        },
        {
            "artifact": "Registration / audit support documents",
            "owner": "Operations / compliance",
            "status": "ready",
            "notes": "Registration certificate and latest audited financial statement packaged with the response.",
        },
    ]


def build_katch_evaluation_rfq_payload(
    *,
    donor_id: str,
    project: str,
    country: str,
    input_context: Dict[str, Any],
    evidence_hint: str,
) -> Dict[str, Any]:
    methods = _rfq_methods(input_context) or [
        "Outcome Harvesting",
        "Social Media Analysis",
        "Key Informant Interviews",
        "Focus Group Discussions",
        "Survey of Beneficiaries",
    ]
    deliverables = _rfq_deliverables(input_context) or [
        "Draft Inception Report with Evaluation Design and Work Plan",
        "Final Inception Report with Evaluation Design and Work Plan",
        "Report on field survey data collection",
        "Virtual Event / Workshop",
        "Final Evaluation Report",
        "Stand-alone Brief",
        "Bi-Weekly Updates",
    ]
    background = _clean_text(
        input_context.get("background")
        or input_context.get("project_background")
        or "Performance evaluation for the KATCH project, covering child trafficking prevention, child protection systems, and safe migration outcomes in southern Kazakhstan."
    )
    purpose = _clean_text(
        input_context.get("evaluation_purpose")
        or "Assess project relevance, effectiveness, efficiency, sustainability, and outcomes using a mixed qualitative evaluation design."
    )
    questions = _rfq_questions(input_context) or [
        "How relevant and responsive were KATCH interventions to beneficiary needs and the child trafficking context?",
        "To what extent did implementation achieve intended objectives, targets, and outcome-level change?",
        "How efficient was delivery in relation to time, resources, staffing, and cost-effectiveness?",
        "What project benefits are likely to be sustained after closeout, and what should future programming retain or change?",
    ]
    methodology_overview = (
        "Use a mixed-methods final assessment anchored in KATCH's results framework, combining outcome harvesting, "
        "social media analysis, key informant interviews, focus group discussions, survey inputs, and review of "
        "performance data and project documentation."
    )
    if evidence_hint:
        methodology_overview += f" Proposed methods should be aligned with the RFQ evidence package and donor guidance cues ({evidence_hint})."
    return {
        "proposal_mode": EVALUATION_RFQ_PROPOSAL_MODE,
        "rfq_profile": KATCH_EVALUATION_RFQ_PROFILE,
        "brief": (
            f"Technical proposal for the {project} final assessment in {country}, covering evaluation design, fieldwork, "
            "analysis, reporting, and stakeholder validation under the RFQ structure."
        ),
        "background_context": background,
        "evaluation_purpose": purpose,
        "evaluation_questions": questions,
        "methodology_overview": methodology_overview,
        "methodology_components": _build_method_components(methods, project=project, country=country),
        "team_composition": [
            {
                "role": "Team Leader / Evaluation Specialist",
                "responsibility": "Lead evaluation design, coordination, stakeholder communication, and final synthesis.",
            },
            {
                "role": "Evaluation Expert / Analyst",
                "responsibility": "Support data collection tools, analysis, and extraction of findings and recommendations.",
            },
            {
                "role": "Field Research Coordinator",
                "responsibility": "Manage scheduling, local logistics, consent protocols, and secure data collection.",
            },
        ],
        "key_personnel": [
            {
                "name": "Proposed Team Lead",
                "role": "Team Leader / Evaluation Specialist",
                "qualifications": "At least 5 years of trafficking, migration, child protection, or comparable final-evaluation experience with donor-facing reporting.",
                "level_of_effort": "Technical leadership across inception, fieldwork, validation, and final reporting",
                "cv_status": "ready",
            },
            {
                "name": "Proposed Evaluation Analyst",
                "role": "Evaluation Expert / Analyst",
                "qualifications": "Mixed-methods evaluation analyst with qualitative coding, survey analysis, and reporting experience.",
                "level_of_effort": "Analysis support, evidence synthesis, and report drafting",
                "cv_status": "ready",
            },
            {
                "name": "Proposed Field Coordinator",
                "role": "Field Research Coordinator",
                "qualifications": "Field coordination lead with respondent safeguarding, logistics, and secure data handling experience.",
                "level_of_effort": "Field scheduling, respondent coordination, and data collection quality control",
                "cv_status": "ready",
            },
        ],
        "deliverables": _build_katch_deliverable_rows(deliverables),
        "workplan_summary": [
            "Phase I - Engagement: inception meeting, desk review, evaluation design, and work plan approval.",
            "Phase II - Research and Data Collection: fieldwork, interviews, FGDs, beneficiary survey, and data cleaning.",
            "Phase III - Analysis and Reporting: draft report, validation workshop, final report, and stand-alone brief.",
        ],
        "assumptions_risks": [
            "Government, partner, and beneficiary interview access remains feasible within the fieldwork window.",
            "Do-no-harm and confidentiality requirements are maintained for sensitive respondent groups.",
            "Data availability and translation requirements remain manageable during the inception phase.",
        ],
        "organization_information": (
            "Provide legal business name, authorized contact, business registration evidence, organizational profile, "
            "and operating status in Central Asia. Attach registration certificate and latest audited financial statement."
        ),
        "technical_approach_summary": (
            "Describe the proposed approaches for addressing the evaluation questions, including document review, "
            "sampling, qualitative and quantitative methods, data analysis approach, software, risks, limitations, "
            "and ethical safeguards."
        ),
        "sampling_plan": (
            "Sampling should cover KATCH staff, government and local authorities, NGO partners, survivor advisory "
            "stakeholders, Child CTIP Champions, and a bounded sample of beneficiaries, with final numbers refined in inception."
        ),
        "analytical_software": ["Qualitative coding software", "Spreadsheet/statistical analysis tools"],
        "ethical_considerations": [
            "Voluntary participation and informed consent",
            "Anonymization and secure storage of sensitive data",
            "Trauma-informed interview practice and do-no-harm safeguards",
            "Approved adult accompaniment where minors are interviewed",
        ],
        "level_of_effort_summary": (
            "Provide an activity-based level of effort by role and phase, showing person-days for engagement, "
            "fieldwork, analysis, workshop preparation, and final reporting."
        ),
        "technical_experience_summary": (
            "Summarize 3-5 years of evaluation and assessment experience in trafficking in persons, migration, "
            "child protection, or comparable donor-funded development sectors, with verified references."
        ),
        "sample_outputs_summary": (
            "Attach one or more sample technical outputs from comparable final evaluations, end-line studies, or "
            "multidimensional development-sector assessments."
        ),
        "financial_summary": (
            "Provide a separate financial proposal companion that aligns activity-based level of effort, fieldwork, "
            "travel, analysis, workshop, and reporting costs to the technical work plan and deliverable schedule."
        ),
        "cost_structure": _build_katch_cost_structure(),
        "pricing_assumptions": [
            "Professional fees should map directly to named roles and person-days in the level-of-effort matrix.",
            "Travel and fieldwork assumptions should reflect actual field coverage, respondent access, and workshop modality.",
            "Currency, taxes, and reimbursable-cost treatment should be stated explicitly in the financial package.",
        ],
        "payment_schedule_summary": (
            "Use milestone-based invoicing tied to inception approval, fieldwork completion, draft report submission, "
            "and final report / brief acceptance."
        ),
        "submission_package_checklist": _build_katch_submission_package_checklist(),
        "annex_readiness": [
            "Registration certificate and latest audited financial statement",
            "CVs for key personnel",
            "Sample technical output(s)",
            "Activity-based work plan / Gantt chart",
            "Activity-based level of effort matrix",
            "Financial proposal companion / budget note",
        ],
        "compliance_matrix": _build_katch_compliance_matrix(),
    }


def build_evaluation_rfq_fallback_payload(
    *,
    donor_id: str,
    project: str,
    country: str,
    input_context: Dict[str, Any],
    evidence_hint: str,
) -> Dict[str, Any]:
    if is_katch_evaluation_rfq(input_context):
        return build_katch_evaluation_rfq_payload(
            donor_id=donor_id,
            project=project,
            country=country,
            input_context=input_context,
            evidence_hint=evidence_hint,
        )
    background = _clean_text(
        input_context.get("background")
        or input_context.get("project_background")
        or input_context.get("problem")
        or f"{project} requires a structured performance evaluation response in {country}."
    )
    purpose = _clean_text(
        input_context.get("evaluation_purpose")
        or input_context.get("purpose")
        or f"Deliver a credible, decision-useful performance evaluation technical proposal for {project}."
    )
    methods = _rfq_methods(input_context) or [
        "Outcome Harvesting",
        "Social Media Analysis",
        "Focus Group Discussions",
        "Survey of Beneficiaries",
    ]
    deliverables = _rfq_deliverables(input_context) or [
        "Inception Report, Evaluation Design and Work Plan",
        "Bi-Weekly Updates",
        "Draft Evaluation Report",
        "Stand-alone Brief",
        "Final Evaluation Report",
    ]
    questions = _rfq_questions(input_context) or [
        f"What results and outcome-level changes can be credibly attributed to {project}?",
        "Which implementation factors most strongly influenced performance and stakeholder uptake?",
        "What practical recommendations should guide follow-on programming or partner action?",
    ]
    methodology_overview = (
        f"Use a mixed-methods performance evaluation design for {project} in {country}, combining "
        f"{', '.join(methods[:3])}, triangulated against project documentation and partner records."
    )
    if evidence_hint:
        methodology_overview += f" Design choices should align with available guidance and evidence cues ({evidence_hint})."
    return {
        "proposal_mode": EVALUATION_RFQ_PROPOSAL_MODE,
        "brief": (
            f"Technical response for a {donor_id} evaluation RFQ covering evaluation design, fieldwork, "
            f"quality assurance, and final reporting for {project} in {country}."
        ),
        "background_context": background,
        "evaluation_purpose": purpose,
        "evaluation_questions": questions,
        "methodology_overview": methodology_overview,
        "methodology_components": _build_method_components(methods, project=project, country=country),
        "team_composition": _build_team_roles(project),
        "key_personnel": _build_key_personnel(project),
        "deliverables": _build_deliverable_rows(deliverables),
        "workplan_summary": [
            "Mobilize and validate the inception package before fieldwork.",
            "Run field data collection and evidence validation against the agreed evaluation matrix.",
            "Submit draft findings, absorb client feedback, and finalize the report package.",
        ],
        "assumptions_risks": [
            "Client access to project records, stakeholder lists, and prior reporting remains timely.",
            "Field access and respondent scheduling allow the agreed evidence plan to be completed within the RFQ timeline.",
        ],
        "financial_summary": "Provide a separate financial proposal companion tied to the technical work plan and staffing structure.",
        "cost_structure": [],
        "pricing_assumptions": [],
        "payment_schedule_summary": "",
        "submission_package_checklist": [],
        "compliance_matrix": [],
    }
