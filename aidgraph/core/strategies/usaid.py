# aidgraph/core/strategies/usaid.py

from __future__ import annotations

from typing import Type
from pydantic import BaseModel
from aidgraph.core.donor_strategy import DonorStrategy

class USAID_DevelopmentObjective(BaseModel):
    objective_id: str
    title: str
    description: str

class USAID_TOC(BaseModel):
    objectives: list[USAID_DevelopmentObjective]

class USAIDStrategy(DonorStrategy):
    donor_id: str = "USAID"

    def get_toc_schema(self) -> Type[USAID_TOC]:
        return USAID_TOC

    def get_rag_collection(self) -> str:
        return "usaid_ads201"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": "Draft ToC for USAID using its Development Objective structure.",
            "MEL_Specialist": "Map indicators to USAID-style results framework.",
            "Red_Team_Critic": "Critically review ToC and MEL alignment with USAID rules."
        }
