# aidgraph/core/strategies/factory.py

from __future__ import annotations

from aidgraph.core.strategies.usaid import USAIDStrategy
from aidgraph.core.strategies.eu import EUStrategy
from aidgraph.core.strategies.worldbank import WorldBankStrategy

def strategy_factory(donor_id: str):
    """Factory function to get the appropriate donor strategy."""
    d = donor_id.lower()
    if d == "usaid":
        return USAIDStrategy()
    if d == "eu":
        return EUStrategy()
    if d == "worldbank":
        return WorldBankStrategy()
    raise ValueError(f"Unknown donor_id: {donor_id}")
