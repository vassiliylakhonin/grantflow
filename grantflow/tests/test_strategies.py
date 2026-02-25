# grantflow/tests/test_strategies.py

import pytest

from grantflow.core.strategies.catalog import list_supported_donors
from grantflow.core.strategies.eu import EUStrategy
from grantflow.core.strategies.factory import DonorFactory, strategy_factory
from grantflow.core.strategies.giz import GIZStrategy
from grantflow.core.strategies.state_department import StateDepartmentStrategy
from grantflow.core.strategies.usaid import USAIDStrategy
from grantflow.core.strategies.worldbank import WorldBankStrategy


def test_usaid_strategy():
    strategy = strategy_factory("USAID")
    assert isinstance(strategy, USAIDStrategy)
    assert strategy.donor_id == "USAID"
    assert strategy.get_rag_collection() == "usaid_ads201"
    prompts = strategy.get_system_prompts()
    assert "Architect" in prompts
    assert "MEL_Specialist" in prompts
    assert "Red_Team_Critic" in prompts


def test_eu_strategy():
    strategy = strategy_factory("EU")
    assert isinstance(strategy, EUStrategy)
    assert strategy.donor_id == "EU"
    assert strategy.get_rag_collection() == "eu_intpa"


def test_worldbank_strategy():
    strategy = strategy_factory("WorldBank")
    assert isinstance(strategy, WorldBankStrategy)
    assert strategy.donor_id == "WorldBank"
    assert strategy.get_rag_collection() == "worldbank_ads301"


def test_giz_strategy():
    strategy = strategy_factory("giz")
    assert isinstance(strategy, GIZStrategy)
    assert strategy.get_rag_collection() == "giz_guidance"
    prompts = strategy.get_system_prompts()
    assert "Architect" in prompts and "MEL_Specialist" in prompts and "Red_Team_Critic" in prompts


def test_state_department_strategy():
    strategy = strategy_factory("us_state_department")
    assert isinstance(strategy, StateDepartmentStrategy)
    assert strategy.get_rag_collection() == "us_state_department_guidance"
    prompts = strategy.get_system_prompts()
    assert "Architect" in prompts and "MEL_Specialist" in prompts and "Red_Team_Critic" in prompts


def test_donor_factory_aliases():
    assert isinstance(DonorFactory.get_strategy("usaid.gov"), USAIDStrategy)
    assert isinstance(DonorFactory.get_strategy("european-union"), EUStrategy)
    assert isinstance(DonorFactory.get_strategy("world_bank"), WorldBankStrategy)
    # New catalog aliases
    assert DonorFactory.get_strategy("undp").get_rag_collection() == "un_agencies_guidance"
    assert isinstance(DonorFactory.get_strategy("giz"), GIZStrategy)
    assert isinstance(DonorFactory.get_strategy("state_department"), StateDepartmentStrategy)
    assert DonorFactory.get_strategy("gates").get_rag_collection() == "gates_foundation_guidance"


def test_all_catalog_donors_supported():
    donors = list_supported_donors()
    assert len(donors) >= 30
    for donor in donors:
        strategy = DonorFactory.get_strategy(donor["id"])
        assert strategy is not None
        assert strategy.get_rag_collection()


def test_unknown_donor():
    with pytest.raises(ValueError):
        strategy_factory("UnknownDonor")
