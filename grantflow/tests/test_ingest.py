import pytest

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
