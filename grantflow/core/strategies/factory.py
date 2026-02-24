# grantflow/core/strategies/factory.py

from __future__ import annotations

from grantflow.core.donor_strategy import DonorStrategy
from grantflow.core.strategies.catalog import list_supported_donors, resolve_donor_record
from grantflow.core.strategies.eu import EUStrategy
from grantflow.core.strategies.generic import GenericDonorStrategy
from grantflow.core.strategies.giz import GIZStrategy
from grantflow.core.strategies.state_department import StateDepartmentStrategy
from grantflow.core.strategies.usaid import USAIDStrategy
from grantflow.core.strategies.worldbank import WorldBankStrategy


def strategy_factory(donor_id: str) -> DonorStrategy:
    """Factory function to get the appropriate donor strategy."""
    record = resolve_donor_record(donor_id)
    if record is None:
        raise ValueError(f"Unknown donor_id: {donor_id}")

    strategy_kind = record.get("strategy", "generic")
    if strategy_kind == "usaid":
        return USAIDStrategy()
    if strategy_kind == "eu":
        return EUStrategy()
    if strategy_kind == "worldbank":
        return WorldBankStrategy()
    if strategy_kind == "giz":
        return GIZStrategy()
    if strategy_kind == "state_department":
        return StateDepartmentStrategy()
    return GenericDonorStrategy(record)


class DonorFactory:
    @staticmethod
    def get_strategy(donor: str) -> DonorStrategy:
        return strategy_factory(donor)

    @staticmethod
    def list_supported() -> list[dict]:
        return list_supported_donors()
