# grantflow/core/strategies/eu.py

from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from grantflow.core.donor_strategy import DonorStrategy


class EU_OverallObjective(BaseModel):
    objective_id: str
    title: str
    rationale: str


class EU_TOC(BaseModel):
    overall_objective: EU_OverallObjective


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
