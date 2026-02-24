from __future__ import annotations

from typing import Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


class StateDeptObjective(BaseModel):
    objective: str = Field(description="Program objective aligned to foreign assistance priorities")
    line_of_effort: str = Field(description="Diplomacy / governance / rights / security / public affairs line of effort")
    expected_change: str = Field(description="Expected measurable change")


class StateDeptTOC(BaseModel):
    strategic_context: str = Field(description="Country/context summary relevant to the funding call")
    program_goal: str = Field(description="Overall program goal")
    objectives: list[StateDeptObjective] = Field(default_factory=list)
    stakeholder_map: list[str] = Field(default_factory=list)
    risk_mitigation: list[str] = Field(default_factory=list)


class StateDepartmentStrategy(DonorStrategy):
    donor_id: str = "U.S. Department of State"

    def get_toc_schema(self) -> Type[StateDeptTOC]:
        return StateDeptTOC

    def get_rag_collection(self) -> str:
        return "us_state_department_guidance"

    def get_system_prompts(self) -> dict:
        return {
            "Architect": (
                "You are a proposal architect for U.S. Department of State assistance programs. Build a clear, policy-aligned "
                "results logic tailored to democracy, human rights, civic space, public diplomacy, or stabilization objectives. "
                "Keep objectives realistic, context-specific, and operationally implementable."
            ),
            "MEL_Specialist": (
                "You are a monitoring and evaluation specialist for U.S. Department of State programs. Use only the donor-specific "
                "RAG namespace 'us_state_department_guidance' and produce indicators with explicit justification and citations. "
                "Prefer indicators suitable for sensitive operating environments and rights/governance programming."
            ),
            "Red_Team_Critic": (
                "You are a strict U.S. Department of State reviewer. Check policy alignment, political/context realism, "
                "stakeholder logic, safeguarding of participants, and measurability. Penalize vague outcomes and weak risk mitigation."
            ),
        }
