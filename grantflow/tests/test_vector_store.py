# grantflow/tests/test_vector_store.py

from grantflow.memory_bank.vector_store import VectorStore, vector_store


def test_vector_store_upsert_query():
    """Проверяет basic upsert и query."""
    namespace = "test_namespace"

    # Upsert
    vector_store.upsert(namespace=namespace, documents=["Test document 1", "Test document 2"], ids=["test_1", "test_2"])

    # Query
    results = vector_store.query(namespace, "Test document", top_k=2)
    assert len(results) >= 1
    assert "document" in results[0]


def test_vector_store_stats():
    """Проверяет статистику коллекции."""
    stats = vector_store.get_stats("test_namespace")
    assert "namespace" in stats
    assert "document_count" in stats
    assert stats["document_count"] >= 2


def test_collection_name_normalizes_namespace_tokens():
    store = VectorStore()
    store.prefix = "grantflow"
    collection = store._collection_name(" Tenant A/USAID ADS 201 :: Phase#1 ")
    assert collection == "grantflow_tenant_a_usaid_ads_201_phase_1"


def test_normalize_namespace_falls_back_to_default():
    assert VectorStore.normalize_namespace("   ") == "default"
