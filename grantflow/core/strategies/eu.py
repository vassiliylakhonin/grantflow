# grantflow/core/strategies/eu.py

from __future__ import annotations

from typing import Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


class EU_OverallObjective(BaseModel):
    objective_id: str = Field(description="EU intervention logic identifier for overall objective")
    title: str = Field(description="Overall objective title")
    rationale: str = Field(description="Why this objective is relevant for donor and country context")


class EU_SpecificObjective(BaseModel):
    objective_id: str = Field(description="Specific objective identifier")
    title: str = Field(description="Specific objective title")
    rationale: str = Field(description="How this objective contributes to the overall objective")


class EU_Outcome(BaseModel):
    outcome_id: str = Field(description="Outcome identifier")
    title: str = Field(description="Expected outcome title")
    expected_change: str = Field(description="Description of measurable expected change")


class EU_TOC(BaseModel):
    overall_objective: EU_OverallObjective
    specific_objectives: list[EU_SpecificObjective] = Field(
        default_factory=list,
        description="Specific objectives linked to intervention logic",
    )
    expected_outcomes: list[EU_Outcome] = Field(default_factory=list, description="Expected outcomes")
    assumptions: list[str] = Field(default_factory=list, description="Key assumptions")
    risks: list[str] = Field(default_factory=list, description="Key implementation risks")


class EUStrategy(DonorStrategy):
    donor_id: str = "EU"

    def get_toc_schema(self) -> Type[EU_TOC]:
        return EU_TOC

    def get_rag_collection(self) -> str:
        return "eu_intpa"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": "Draft ToC with EU Intervention Logic.",
            "MEL_Specialist": "Anchor indicators to EU logframe expectations.",
            "Red_Team_Critic": "Find gaps with EU-specific rules.",
        }
