from __future__ import annotations

from typing import List, Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


# --- 1. Strict Hierarchical Pydantic Models for USAID ---
class USAID_Indicator(BaseModel):
    indicator_code: str = Field(description="Standard Foreign Assistance Indicator Code (e.g., HL.9-1)")
    name: str = Field(description="Full name of the indicator")
    target: str = Field(description="Numeric or qualitative target")
    justification: str = Field(description="Logical reasoning for choosing this indicator for this specific result")
    citation: str = Field(description="Exact reference from USAID ADS 201 or standard indicator handbook")


class USAID_Output(BaseModel):
    output_id: str = Field(description="e.g., Output 1.1.1")
    description: str = Field(description="Tangible product or service delivered")
    indicators: List[USAID_Indicator]


class USAID_IntermediateResult(BaseModel):
    ir_id: str = Field(description="e.g., IR 1.1")
    description: str = Field(description="Lower-level result contributing to the DO")
    outputs: List[USAID_Output]


class USAID_DevelopmentObjective(BaseModel):
    do_id: str = Field(description="e.g., DO 1")
    description: str = Field(description="Highest-level strategic objective")
    intermediate_results: List[USAID_IntermediateResult]


class USAID_TOC(BaseModel):
    project_goal: str = Field(description="The ultimate impact goal of the project")
    development_objectives: List[USAID_DevelopmentObjective]
    critical_assumptions: List[str] = Field(description="External conditions necessary for success")


# --- 2. The Strategy Implementation ---
class USAIDStrategy(DonorStrategy):
    donor_id: str = "USAID"

    def get_toc_schema(self) -> Type[USAID_TOC]:
        return USAID_TOC

    def get_rag_collection(self) -> str:
        return "usaid_ads201"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": (
                "You are an elite USAID Proposal Architect. Your task is to design a Theory of Change "
                "strictly adhering to the USAID Results Framework hierarchy: Goal -> Development Objective (DO) "
                "-> Intermediate Result (IR) -> Outputs. Every level must logically cascade into the next. "
                "Ensure that critical assumptions are realistic for the targeted region."
            ),
            "MEL_Specialist": (
                "You are a USAID Monitoring, Evaluation, and Learning (MEL) Director. "
                "You must attach precise Standard Foreign Assistance Indicators to the provided ToC. "
                "You MUST query the vector database to find the exact official indicator codes. "
                "Never invent or hallucinate indicator codes. Always provide a clear justification and citation."
            ),
            "Red_Team_Critic": (
                "You are a strict USAID Contracting/Agreement Officer evaluating a proposal draft. "
                "Score the proposal out of 10. You must ruthlessly search for: "
                "1) Weak causal links between Outputs and IRs (the 'If/Then' logic). "
                "2) Unrealistic assumptions. "
                "3) Missing cross-cutting themes (Gender equality, Climate resilience). "
                "If the score is below 8, output specific actionable feedback for the Architect to fix. "
                "Do not be polite; be bureaucratically precise."
            ),
        }
