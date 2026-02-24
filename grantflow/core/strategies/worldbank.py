# grantflow/core/strategies/worldbank.py

from __future__ import annotations

from typing import Type
from pydantic import BaseModel
from grantflow.core.donor_strategy import DonorStrategy

class WB_DevelopmentObjective(BaseModel):
    objective_id: str
    title: str
    description: str

class WorldBank_TOC(BaseModel):
    objectives: list[WB_DevelopmentObjective]

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
            "Red_Team_Critic": "Critically review ToC and MEL alignment with WB rules."
        }
