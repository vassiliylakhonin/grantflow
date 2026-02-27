import pytest

import grantflow.memory_bank.ingest as ingest_module
from grantflow.memory_bank.ingest import chunk_pages, chunk_text


def test_chunk_text_validates_chunk_size():
    with pytest.raises(ValueError, match="chunk_size must be > 0"):
        chunk_text("abc", chunk_size=0)


def test_chunk_text_validates_overlap_bounds():
    with pytest.raises(ValueError, match="overlap must be >= 0"):
        chunk_text("abc", chunk_size=10, overlap=-1)

    with pytest.raises(ValueError, match="overlap must be < chunk_size"):
        chunk_text("abc", chunk_size=10, overlap=10)


def test_chunk_text_splits_with_overlap():
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)
    assert chunks == ["abcd", "defg", "ghij", "j"]


def test_chunk_pages_includes_page_and_chunk_trace_metadata():
    records = chunk_pages(["abcd", "wxyz1234"], chunk_size=4, overlap=1)
    assert records

    first = records[0]
    assert first["text"] == "abcd"
    assert first["page"] == 1
    assert first["page_start"] == 1
    assert first["page_end"] == 1
    assert first["chunk"] == 0
    assert first["page_chunk"] == 0

    second_page = [r for r in records if r["page"] == 2]
    assert second_page
    assert second_page[0]["chunk"] >= 1


def test_ingest_pdf_prefers_uploaded_filename_as_source(monkeypatch):
    monkeypatch.setattr(ingest_module, "load_pdf_pages", lambda _: ["example page"])

    calls = {}

    def fake_upsert(namespace, ids, documents, metadatas=None):
        calls["namespace"] = namespace
        calls["ids"] = ids
        calls["documents"] = documents
        calls["metadatas"] = metadatas or []

    monkeypatch.setattr(ingest_module.vector_store, "upsert", fake_upsert)
    monkeypatch.setattr(ingest_module.vector_store, "get_stats", lambda namespace: {"namespace": namespace, "count": 1})

    result = ingest_module.ingest_pdf_to_namespace(
        "/tmp/grantflow_ingest_1234.pdf",
        "usaid_ads201",
        metadata={"uploaded_filename": "usaid_ads201_policy.pdf", "doc_family": "donor_policy"},
    )

    assert result["source"] == "usaid_ads201_policy.pdf"
    assert result["source_path"] == "/tmp/grantflow_ingest_1234.pdf"
    assert calls["namespace"] == "usaid_ads201"
    assert calls["metadatas"]
    assert calls["metadatas"][0]["source"] == "usaid_ads201_policy.pdf"
    assert calls["metadatas"][0]["source_path"] == "/tmp/grantflow_ingest_1234.pdf"
    assert calls["metadatas"][0]["doc_family"] == "donor_policy"
