# aidgraph/tests/test_strategies.py

import pytest
from aidgraph.core.strategies.factory import strategy_factory
from aidgraph.core.strategies.usaid import USAIDStrategy
from aidgraph.core.strategies.eu import EUStrategy
from aidgraph.core.strategies.worldbank import WorldBankStrategy

def test_usaid_strategy():
    """Проверяет USAID стратегию."""
    strategy = strategy_factory("USAID")
    assert isinstance(strategy, USAIDStrategy)
    assert strategy.donor_id == "USAID"
    assert strategy.get_rag_collection() == "usaid_ads201"
    
    prompts = strategy.get_system_prompts()
    assert "Architect" in prompts
    assert "MEL_Specialist" in prompts
    assert "Red_Team_Critic" in prompts

def test_eu_strategy():
    """Проверяет EU стратегию."""
    strategy = strategy_factory("EU")
    assert isinstance(strategy, EUStrategy)
    assert strategy.donor_id == "EU"
    assert strategy.get_rag_collection() == "eu_intpa"

def test_worldbank_strategy():
    """Проверяет World Bank стратегию."""
    strategy = strategy_factory("WorldBank")
    assert isinstance(strategy, WorldBankStrategy)
    assert strategy.donor_id == "WorldBank"
    assert strategy.get_rag_collection() == "worldbank_ads301"

def test_unknown_donor():
    """Проверяет обработку неизвестного донора."""
    with pytest.raises(ValueError):
        strategy_factory("UnknownDonor")
