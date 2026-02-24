# grantflow/core/donor_strategy.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel

class DonorStrategy(ABC):
    """Abstract base class for donor strategies."""
    donor_id: str

    @abstractmethod
    def get_toc_schema(self) -> Type[BaseModel]:
        """Return the Pydantic model class for ToC schema specific to donor."""
        ...

    @abstractmethod
    def get_rag_collection(self) -> str:
        """Return exact ChromaDB namespace for RAG queries for this donor."""
        ...

    @abstractmethod
    def get_system_prompts(self) -> dict:
        """Return persona instructions for Architect, MEL Specialist, and Red Team Critic."""
        ...
