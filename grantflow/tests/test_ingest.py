import pytest

from grantflow.memory_bank.ingest import chunk_text


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
    assert chunks == ["abcd", "defg", "ghij"]
