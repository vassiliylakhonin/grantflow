from __future__ import annotations

from typing import Any, Dict, Type

from pydantic import BaseModel, Field

from grantflow.core.donor_strategy import DonorStrategy


class GenericObjective(BaseModel):
    title: str = Field(description="Result or objective title")
    description: str = Field(description="Objective description")


class GenericTOC(BaseModel):
    project_goal: str = Field(description="Overall project goal")
    objectives: list[GenericObjective] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class GenericDonorStrategy(DonorStrategy):
    def __init__(self, donor_record: Dict[str, Any]) -> None:
        self._record = donor_record
        self.donor_id = donor_record.get("name") or donor_record.get("id") or "Generic Donor"

    def get_toc_schema(self) -> Type[GenericTOC]:
        return GenericTOC

    def get_rag_collection(self) -> str:
        return str(self._record.get("rag_namespace") or "grantflow_generic_guidance")

    def get_system_prompts(self) -> dict:
        donor_name = self._record.get("name", "donor")
        profile = self._record.get("profile", "institutional funding program")
        category = self._record.get("category", "donor")
        site = self._record.get("site", "")
        site_hint = f" Reference official guidance from {site}." if site else ""
        return {
            "Architect": (
                f"You are a proposal architect for {donor_name}. Draft a results chain and Theory of Change "
                f"that matches the expectations of a {category} donor. Focus areas: {profile}.{site_hint}"
            ),
            "MEL_Specialist": (
                f"You are a MEL specialist preparing indicators for {donor_name}. Use only the donor-specific "
                f"RAG namespace '{self.get_rag_collection()}' and provide justification plus citation for each indicator."
            ),
            "Red_Team_Critic": (
                f"You are a strict reviewer for {donor_name}. Score the proposal for logical consistency, donor fit, "
                f"measurable indicators, and implementation realism. Provide concrete revision instructions if score < 8."
            ),
        }
