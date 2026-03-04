from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "check_seeded_corpus.py"
    spec = importlib.util.spec_from_file_location("check_seeded_corpus", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_seeded_corpus_passes_with_expected_donors():
    module = _load_module()
    ok, failures = module.validate_seeded_corpus(
        report_payload={
            "seeded_corpus": {
                "seeded_total": 8,
                "errors": [],
                "donor_counts": {"usaid": 4, "worldbank": 4},
            }
        },
        expected_donors=["usaid", "worldbank"],
        min_seeded_total=1,
        require_no_errors=True,
    )
    assert ok is True
    assert failures == []


def test_validate_seeded_corpus_fails_on_seed_errors_and_missing_donor():
    module = _load_module()
    ok, failures = module.validate_seeded_corpus(
        report_payload={
            "seeded_corpus": {
                "seeded_total": 2,
                "errors": ["line 2: ingest failed"],
                "donor_counts": {"usaid": 2},
            }
        },
        expected_donors=["usaid", "eu"],
        min_seeded_total=1,
        require_no_errors=True,
    )
    assert ok is False
    assert len(failures) == 2
    assert "seeded_corpus.errors is non-empty" in failures[0]
    assert "Expected donor 'eu'" in failures[1]


def test_validate_seeded_corpus_fails_when_seeded_total_too_low():
    module = _load_module()
    ok, failures = module.validate_seeded_corpus(
        report_payload={
            "seeded_corpus": {
                "seeded_total": 0,
                "errors": [],
                "donor_counts": {},
            }
        },
        expected_donors=[],
        min_seeded_total=1,
        require_no_errors=True,
    )
    assert ok is False
    assert len(failures) == 1
    assert "seeded_corpus.seeded_total=0" in failures[0]
