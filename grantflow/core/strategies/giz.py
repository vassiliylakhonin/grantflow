from __future__ import annotations

from typing import Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


class GIZOutcome(BaseModel):
    title: str = Field(description="Outcome title aligned with technical cooperation objectives")
    description: str = Field(description="Outcome statement describing expected change")
    partner_role: str = Field(description="Role of local partner / implementing institution")


class GIZTOC(BaseModel):
    programme_objective: str = Field(description="Overall programme objective")
    outputs: list[str] = Field(default_factory=list, description="Core technical cooperation outputs")
    outcomes: list[GIZOutcome] = Field(default_factory=list)
    sustainability_factors: list[str] = Field(default_factory=list)
    assumptions_risks: list[str] = Field(default_factory=list)


class GIZStrategy(DonorStrategy):
    donor_id: str = "GIZ"

    def get_toc_schema(self) -> Type[GIZTOC]:
        return GIZTOC

    def get_rag_collection(self) -> str:
        return "giz_guidance"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": (
                "You are a GIZ proposal architect for technical cooperation programmes. Build a practical results chain "
                "that emphasizes implementation feasibility, partner institutions, capacity development, and sustainability. "
                "Keep outputs and outcomes operational and realistic for implementation partners."
            ),
            "MEL_Specialist": (
                "You are a GIZ monitoring and results specialist. Use only the donor-specific RAG namespace 'giz_guidance' "
                "to draft measurable indicators with clear justification and citations. Prefer indicators that can be collected "
                "through partner institutions and routine programme monitoring."
            ),
            "Red_Team_Critic": (
                "You are a strict GIZ reviewer. Evaluate coherence between technical assistance activities, partner capacity outcomes, "
                "and sustainability assumptions. Penalize vague outputs, unrealistic institutional change claims, and weak monitoring logic."
            ),
        }
