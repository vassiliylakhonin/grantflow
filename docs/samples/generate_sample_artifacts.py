from __future__ import annotations

import json
from pathlib import Path

from grantflow.exporters.excel_builder import save_xlsx_to_file
from grantflow.exporters.word_builder import save_docx_to_file


def build_sample_payload() -> dict:
    donor_id = "usaid"
    toc_draft = {
        "toc": {
            "brief": (
                "This sanitized sample illustrates the structure of a donor-aligned draft for a public-sector "
                "AI capacity strengthening program. It is not a real proposal submission."
            ),
            "objectives": [
                {
                    "title": "Strengthen institutional capacity for responsible AI use in government workflows",
                    "description": (
                        "Participating agencies adopt supervised AI use practices, governance guidance, and "
                        "pilot workflow improvements tied to service quality and administrative efficiency."
                    ),
                    "citation": "Seed corpus guidance + contextual public administration references",
                },
                {
                    "title": "Improve civil servant competencies for applied AI in priority functions",
                    "description": (
                        "Civil servants complete training and applied labs covering AI literacy, safe use, "
                        "oversight, and workflow design in policy and service delivery contexts."
                    ),
                    "citation": "Training design and competency framework references",
                },
            ],
        },
        "indicators": [
            {
                "name": "% of participating agencies applying approved AI SOPs in pilot workflows",
                "justification": "Tracks institutional adoption beyond training attendance.",
            },
            {
                "name": "% of trained participants scoring above competency threshold in post-test",
                "justification": "Captures competency improvement among trained cohorts.",
            },
        ],
    }
    logframe_draft = {
        "indicators": [
            {
                "indicator_id": "DO-1",
                "name": "% of participating agencies applying approved AI SOPs in pilot workflows",
                "justification": "Measures institutionalization of AI governance and supervised use.",
                "citation": "WB/USAID-style results and SOP adoption verification guidance",
                "baseline": 0,
                "target": "60% by endline",
            },
            {
                "indicator_id": "IR1-1",
                "name": "% of trained participants scoring above competency threshold in post-test",
                "justification": "Measures immediate training outcome before workflow adoption.",
                "citation": "Training assessment methodology note",
                "baseline": "TBD (baseline cohort)",
                "target": "75%",
            },
            {
                "indicator_id": "OUT-1",
                "name": "# civil servants completing cohort modules",
                "justification": "Tracks delivery volume and program reach.",
                "citation": "Attendance and LMS completion records",
                "baseline": 0,
                "target": "600-1000",
            },
        ]
    }
    citations = [
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "used_for": "objective",
            "label": "USAID Program Cycle / Results Logic (seed)",
            "namespace": "usaid_ads201",
            "source": "01_usaid_donor_policy_ads_program_cycle_seed.pdf",
            "page": 2,
            "chunk": 1,
            "chunk_id": "usaid-seed-ads201-p2-c1",
            "citation_confidence": 0.84,
            "confidence_threshold": 0.32,
            "excerpt": "Results design should link activities, outputs, intermediate results, and development objectives.",
        },
        {
            "stage": "architect",
            "citation_type": "rag_claim_support",
            "used_for": "objective",
            "label": "Civil Service AI Competency Framework (seed)",
            "namespace": "usaid_ads201",
            "source": "04_civil_service_ai_competency_framework_seed.pdf",
            "page": 3,
            "chunk": 0,
            "chunk_id": "usaid-seed-competency-p3-c0",
            "citation_confidence": 0.79,
            "confidence_threshold": 0.32,
            "excerpt": "Competency pathways should combine foundational literacy, supervised application, and governance awareness.",
        },
        {
            "stage": "mel",
            "citation_type": "rag_result",
            "used_for": "indicator_selection",
            "label": "Results framework and M&E guidance (seed)",
            "namespace": "usaid_ads201",
            "source": "01_usaid_donor_policy_ads_program_cycle_seed.pdf",
            "page": 4,
            "chunk": 2,
            "chunk_id": "usaid-seed-ads201-p4-c2",
            "citation_confidence": 0.8,
            "excerpt": "Indicators should be tied to decision-making and feasible means of verification.",
        },
    ]
    critic_findings = [
        {
            "finding_id": "finding-001",
            "status": "resolved",
            "severity": "low",
            "section": "toc",
            "code": "OBJECTIVE_SPECIFICITY",
            "message": "Objective wording was broad; revised to emphasize institutional adoption and supervised use.",
            "fix_hint": "Keep measurable adoption language in objective and align with indicator set.",
            "version_id": "toc-v2",
            "source": "llm",
            "label": "OBJECTIVE_SPECIFICITY",
        },
        {
            "finding_id": "finding-002",
            "status": "open",
            "severity": "medium",
            "section": "logframe",
            "code": "BASELINE_TARGET_MISSING",
            "message": "Baseline methodology is described, but baseline values for all participating agencies are still TBD.",
            "fix_hint": "Add baseline plan timeline and agency coverage assumptions before submission.",
            "version_id": "logframe-v1",
            "source": "llm",
            "label": "BASELINE_TARGET_MISSING",
        },
    ]
    review_comments = [
        {
            "comment_id": "comment-001",
            "status": "resolved",
            "section": "toc",
            "author": "program_lead",
            "message": "Clarify institutional adoption vs individual training outcomes in the objective statement.",
            "version_id": "toc-v1",
            "linked_finding_id": "finding-001",
            "ts": "2026-02-26T10:15:00Z",
        },
        {
            "comment_id": "comment-002",
            "status": "open",
            "section": "logframe",
            "author": "mel_advisor",
            "message": "Need baseline collection schedule and source owners before finalizing targets.",
            "version_id": "logframe-v1",
            "linked_finding_id": "finding-002",
            "ts": "2026-02-26T10:24:00Z",
        },
    ]
    return {
        "donor_id": donor_id,
        "toc_draft": toc_draft,
        "logframe_draft": logframe_draft,
        "citations": citations,
        "critic_findings": critic_findings,
        "review_comments": review_comments,
    }


def build_rbm_samples() -> dict:
    return {
        "usaid_ai_civil_service_kazakhstan_2026_2027": {
            "sample_id": "usaid_ai_civil_service_kazakhstan_2026_2027",
            "donor_id": "usaid",
            "program_context": {
                "title": "Responsible AI Capacity for Civil Service",
                "country": "Kazakhstan",
                "time_horizon": {"implementation_months": 24, "impact_horizon_years": "3-5"},
                "problem_summary": (
                    "Public institutions need practical responsible AI competencies and governance procedures to "
                    "deploy AI-enabled services safely and accountably."
                ),
                "target_population": "National and subnational civil servants in participating ministries/agencies",
                "inclusion_priorities": ["women in public administration", "regional agency representation"],
                "assumptions": [
                    "Illustrative budget and participating agency counts; replace during inception.",
                    "Baseline competency and service performance values collected in months 1-2.",
                ],
            },
            "theory_of_change": {
                "if_then": (
                    "If civil servants receive practical responsible AI training and agencies adopt minimum AI "
                    "governance controls, then institutions can improve service quality with safer and more "
                    "accountable AI-enabled workflows."
                ),
                "causal_pathway": [
                    "inputs",
                    "activities",
                    "outputs",
                    "outcomes_skills",
                    "outcomes_institutional_adoption",
                    "outcomes_service_quality",
                    "impact",
                ],
                "key_assumptions": [
                    "Agency leadership allocates staff time for training and implementation.",
                    "Data and digital infrastructure remain available for pilot services.",
                ],
            },
            "logic_model": {
                "inputs": [
                    "Funding, technical team, curriculum, learning platform, ministry partnerships, M&E systems"
                ],
                "activities": [
                    "Baseline assessment",
                    "Modular training and coaching",
                    "AI governance SOP development",
                    "Pilot implementation support",
                ],
                "outputs": [
                    "Civil servants trained and certified",
                    "Agency implementation plans",
                    "Approved AI governance SOP/checklist packages",
                    "Pilot services launched with monitoring dashboards",
                ],
                "outcomes": [
                    "Improved responsible AI competencies among civil servants by month 24",
                    "Institutionalized AI governance controls in participating agencies by month 24",
                    "Improved quality metrics for pilot services by month 24",
                ],
                "impact": "More effective, transparent, and accountable digital public services over 3-5 years.",
            },
            "outcome_indicators": {
                "O1_skills": [
                    {
                        "name": "Share of participants reaching proficiency threshold",
                        "definition_formula": "(participants with post-test >= 70%) / tested participants * 100",
                        "baseline": "22% (assumption; verify baseline month 1)",
                        "target": ">= 75% by month 24",
                        "frequency": "quarterly",
                        "data_source": "LMS tests and practical assessments",
                        "disaggregation": ["sex", "age_band", "ministry", "region"],
                        "owner": "Training manager",
                    },
                    {
                        "name": "Average practical assessment improvement",
                        "definition_formula": "average post-test score - average pre-test score (pp)",
                        "baseline": "0 pp",
                        "target": ">= +25 pp by month 24",
                        "frequency": "quarterly",
                        "data_source": "Pre/post assessment records",
                        "disaggregation": ["sex", "ministry", "role_level"],
                        "owner": "M&E lead",
                    },
                    {
                        "name": "Share of trained staff applying responsible AI tools in workflows",
                        "definition_formula": "(verified users in prior 90 days) / trained staff sampled * 100",
                        "baseline": "10% (assumption; verify month 3)",
                        "target": ">= 60% by month 24",
                        "frequency": "semi-annual",
                        "data_source": "Supervisor verification and workflow artifacts",
                        "disaggregation": ["sex", "ministry", "region"],
                        "owner": "Implementation lead",
                    },
                ],
                "O2_institutional_adoption": [
                    {
                        "name": "Share of agencies with approved AI governance package",
                        "definition_formula": "(agencies with approved SOP package) / participating agencies * 100",
                        "baseline": "0%",
                        "target": "100% by month 24",
                        "frequency": "quarterly",
                        "data_source": "Agency approval records",
                        "disaggregation": ["agency_type", "sector"],
                        "owner": "Governance specialist",
                    },
                    {
                        "name": "Share of new AI initiatives passing governance review pre-launch",
                        "definition_formula": "(initiatives passing review pre-launch) / reviewed initiatives * 100",
                        "baseline": "15% (assumption; verify month 2)",
                        "target": ">= 85% by month 24",
                        "frequency": "quarterly",
                        "data_source": "Governance review logs",
                        "disaggregation": ["agency", "initiative_type"],
                        "owner": "Agency focal points",
                    },
                    {
                        "name": "Median governance review turnaround",
                        "definition_formula": "median days from submission to decision",
                        "baseline": "45 days (assumption)",
                        "target": "<= 20 days by month 24",
                        "frequency": "quarterly",
                        "data_source": "Agency workflow system",
                        "disaggregation": ["agency"],
                        "owner": "Program operations manager",
                    },
                ],
            },
            "sdg_alignment": [
                {"result": "Outcome 1", "goal": "SDG 4", "target": "4.4", "rationale": "Digital skills development"},
                {
                    "result": "Outcome 2",
                    "goal": "SDG 16",
                    "target": "16.6",
                    "rationale": "Effective and accountable institutions",
                },
                {
                    "result": "Outcome 3",
                    "goal": "SDG 16",
                    "target": "16.6",
                    "rationale": "Improved quality and accountability of services",
                },
            ],
            "data_collection_plan": [
                {"component": "baseline_study", "method": "assessment + mapping", "frequency": "once (months 1-2)", "owner": "M&E lead"},
                {"component": "routine_monitoring", "method": "LMS and admin records", "frequency": "monthly/quarterly", "owner": "Training manager"},
                {"component": "midline", "method": "outcome review", "frequency": "month 12", "owner": "Program director"},
                {"component": "endline", "method": "repeat baseline instruments", "frequency": "month 24", "owner": "External evaluator"},
                {"component": "follow_up", "method": "persistence check", "frequency": "6 and 12 months post-close", "owner": "Program team"},
            ],
        },
        "eu_youth_employment_jordan_2026_2028": {
            "sample_id": "eu_youth_employment_jordan_2026_2028",
            "donor_id": "eu",
            "program_context": {
                "title": "Youth Employment and SME Skills Pathways",
                "country": "Jordan",
                "time_horizon": {"implementation_months": 30, "impact_horizon_years": "3-5"},
                "problem_summary": (
                    "Youth face high unemployment and mismatch between labor-market needs and practical skills, "
                    "especially for women and vulnerable young people outside major urban centers."
                ),
                "target_population": "Youth aged 18-29, with priority for women and low-income participants",
                "inclusion_priorities": ["women", "youth with disabilities", "governorates outside Amman"],
                "assumptions": [
                    "Labor demand remains sufficient in target sectors (digital services, light manufacturing, tourism services).",
                    "Private-sector partners maintain internship and placement commitments.",
                ],
            },
            "theory_of_change": {
                "if_then": (
                    "If youth receive market-relevant technical and employability training, and SMEs engage in "
                    "co-designed internship and placement pathways, then youth employment and retention will "
                    "increase, including for women and underserved groups."
                ),
                "causal_pathway": [
                    "inputs",
                    "activities",
                    "outputs",
                    "outcomes_skills_and_placement",
                    "outcomes_retention_and_income",
                    "impact",
                ],
                "key_assumptions": [
                    "Training quality remains aligned with employer demand.",
                    "Participant barriers (transport/childcare) are partially mitigated by program support.",
                ],
            },
            "logic_model": {
                "inputs": [
                    "EU funding, training providers, employer network, placement coordinators, support services budget"
                ],
                "activities": [
                    "Employer-informed curriculum design",
                    "Technical and soft-skills cohorts",
                    "Career coaching and placement support",
                    "SME internship agreements and retention mentoring",
                ],
                "outputs": [
                    "Youth completed certified training tracks",
                    "SME internships and interviews facilitated",
                    "Career plans and job-readiness portfolios completed",
                    "Employer feedback loops operational",
                ],
                "outcomes": [
                    "Higher placement rate for graduates within 6 months",
                    "Higher employment retention at 12 months",
                    "Improved median earnings among employed graduates",
                ],
                "impact": "Reduced youth unemployment pressure and improved inclusive economic participation over 3-5 years.",
            },
            "outcome_indicators": {
                "O1_placement": [
                    {
                        "name": "Graduate placement rate within 6 months",
                        "definition_formula": "(graduates employed/self-employed within 6 months) / total graduates * 100",
                        "baseline": "28% (assumption; verify in baseline labor-market scan)",
                        "target": ">= 65% by month 30",
                        "frequency": "quarterly",
                        "data_source": "Follow-up tracer surveys + employer verification",
                        "disaggregation": ["sex", "age_band", "governorate", "disability_status"],
                        "owner": "Placement coordinator",
                    },
                    {
                        "name": "Share of women graduates placed within 6 months",
                        "definition_formula": "(women graduates placed within 6 months) / women graduates * 100",
                        "baseline": "20% (assumption)",
                        "target": ">= 55% by month 30",
                        "frequency": "quarterly",
                        "data_source": "Tracer surveys + HR confirmations",
                        "disaggregation": ["governorate", "sector"],
                        "owner": "Gender and inclusion officer",
                    },
                    {
                        "name": "SME satisfaction with graduate job readiness",
                        "definition_formula": "(SMEs rating graduates >= 4 on 5-point readiness scale) / responding SMEs * 100",
                        "baseline": "35% (assumption)",
                        "target": ">= 80% by month 30",
                        "frequency": "semi-annual",
                        "data_source": "Employer feedback survey",
                        "disaggregation": ["sector", "firm_size"],
                        "owner": "Private-sector engagement lead",
                    },
                ],
                "O2_retention_income": [
                    {
                        "name": "12-month employment retention rate",
                        "definition_formula": "(graduates employed at 12 months after placement) / graduates placed * 100",
                        "baseline": "45% (assumption)",
                        "target": ">= 75% by month 30",
                        "frequency": "semi-annual",
                        "data_source": "Tracer surveys + payroll/employer confirmation",
                        "disaggregation": ["sex", "governorate", "sector"],
                        "owner": "M&E lead",
                    },
                    {
                        "name": "Median earnings change among employed graduates",
                        "definition_formula": "((median monthly earnings at follow-up - baseline) / baseline) * 100",
                        "baseline": "0% change",
                        "target": ">= +30% by month 30",
                        "frequency": "semi-annual",
                        "data_source": "Participant earnings survey",
                        "disaggregation": ["sex", "governorate", "sector"],
                        "owner": "M&E lead",
                    },
                    {
                        "name": "Share of graduates employed in trained occupation",
                        "definition_formula": "(graduates employed in field aligned with training) / employed graduates * 100",
                        "baseline": "40% (assumption)",
                        "target": ">= 70% by month 30",
                        "frequency": "quarterly",
                        "data_source": "Tracer survey and employer job-role verification",
                        "disaggregation": ["sex", "training_track"],
                        "owner": "Program manager",
                    },
                ],
            },
            "sdg_alignment": [
                {"result": "Outcome 1", "goal": "SDG 8", "target": "8.6", "rationale": "Reduce youth not in employment, education, or training"},
                {"result": "Outcome 2", "goal": "SDG 8", "target": "8.5", "rationale": "Decent work and equal pay opportunity"},
                {"result": "Outcome 1/2", "goal": "SDG 5", "target": "5.5", "rationale": "Economic participation and leadership opportunities for women"},
                {"result": "Impact", "goal": "SDG 1", "target": "1.2", "rationale": "Income gains contribute to poverty reduction"},
            ],
            "data_collection_plan": [
                {"component": "baseline_scan", "method": "labor market + participant baseline survey", "frequency": "months 1-3", "owner": "M&E team"},
                {"component": "cohort_monitoring", "method": "attendance, completion, assessments", "frequency": "monthly", "owner": "Training partners"},
                {"component": "placement_tracking", "method": "tracer and employer verification", "frequency": "quarterly", "owner": "Placement team"},
                {"component": "retention_followup", "method": "3/6/12-month follow-up windows", "frequency": "rolling", "owner": "M&E team"},
                {"component": "data_quality_assurance", "method": "spot checks, duplicate checks, source verification", "frequency": "quarterly", "owner": "M&E lead"},
            ],
        },
    }


def main() -> int:
    samples_dir = Path(__file__).resolve().parent
    samples_dir.mkdir(parents=True, exist_ok=True)

    payload = build_sample_payload()
    donor_id = payload["donor_id"]

    save_docx_to_file(
        payload["toc_draft"],
        donor_id,
        str(samples_dir / "grantflow-sample-toc-review-package.docx"),
        citations=payload["citations"],
        critic_findings=payload["critic_findings"],
        review_comments=payload["review_comments"],
    )
    save_xlsx_to_file(
        payload["logframe_draft"],
        donor_id,
        str(samples_dir / "grantflow-sample-logframe-review-package.xlsx"),
        citations=payload["citations"],
        critic_findings=payload["critic_findings"],
        review_comments=payload["review_comments"],
    )

    (samples_dir / "grantflow-sample-export-payload.json").write_text(
        json.dumps(
            {
                "payload": {
                    "state": {
                        "toc_draft": payload["toc_draft"],
                        "logframe_draft": payload["logframe_draft"],
                        "citations": payload["citations"],
                        "critic_notes": {"fatal_flaws": payload["critic_findings"]},
                    },
                    "critic_findings": payload["critic_findings"],
                    "review_comments": payload["review_comments"],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    rbm_samples = build_rbm_samples()
    (samples_dir / "rbm-sample-usaid-ai-civil-service-kazakhstan.json").write_text(
        json.dumps(rbm_samples["usaid_ai_civil_service_kazakhstan_2026_2027"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (samples_dir / "rbm-sample-eu-youth-employment-jordan.json").write_text(
        json.dumps(rbm_samples["eu_youth_employment_jordan_2026_2028"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
