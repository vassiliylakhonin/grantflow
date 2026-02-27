# grantflow/core/strategies/worldbank.py

from __future__ import annotations

from typing import Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


class WB_DevelopmentObjective(BaseModel):
    objective_id: str = Field(description="Objective identifier")
    title: str = Field(description="Objective title")
    description: str = Field(description="Objective description")


class WB_Result(BaseModel):
    result_id: str = Field(description="Result identifier")
    title: str = Field(description="Result title")
    description: str = Field(description="Result description")
    indicator_focus: str = Field(description="Indicator focus for monitoring progress")


class WorldBank_TOC(BaseModel):
    project_development_objective: str = Field(description="Project Development Objective (PDO)")
    objectives: list[WB_DevelopmentObjective] = Field(default_factory=list)
    results_chain: list[WB_Result] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class WorldBankStrategy(DonorStrategy):
    donor_id: str = "WorldBank"

    def get_toc_schema(self) -> Type[WorldBank_TOC]:
        return WorldBank_TOC

    def get_rag_collection(self) -> str:
        return "worldbank_ads301"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": "Draft ToC for World Bank using its intervention logic.",
            "MEL_Specialist": "Map indicators to WB-style results framework.",
            "Red_Team_Critic": "Critically review ToC and MEL alignment with WB rules.",
        }
