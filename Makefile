.PHONY: deps-guard qa-fast qa-hitl eval-grounded-ab eval-grounded-tail eval-llm-sampled eval-llm-grounded-strict eval-rbm-samples refresh-grounded-baseline

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
EVAL_ARTIFACTS_DIR ?= eval-artifacts
GROUNDED_CASES_FILE ?= grantflow/eval/cases/grounded_cases.json
GROUNDED_TAIL_CASES_FILE ?= grantflow/eval/cases/grounded_tail_cases.json
LLM_GROUNDED_STRICT_CASES_FILE ?= grantflow/eval/cases/llm_grounded_strict_cases.json
GROUNDED_SEED_MANIFEST ?= docs/rag_seed_corpus/ingest_manifest.jsonl
GROUNDED_BASELINE ?= grantflow/eval/fixtures/grounded_regression_snapshot.json
GROUNDED_TAIL_BASELINE ?= grantflow/eval/fixtures/grounded_tail_regression_snapshot.json
GROUNDED_GUARD_DONORS ?= usaid,eu,worldbank,state_department
GROUNDED_MAX_NON_RETRIEVAL ?= 0.25
GROUNDED_MIN_RETRIEVAL_GROUNDED ?= 0.75
GROUNDED_MAX_TRACEABILITY_GAP ?= 0.10
GROUNDED_MIN_NON_RETRIEVAL_IMPROVEMENT ?= 0.25
GROUNDED_MIN_RETRIEVAL_GROUNDED_IMPROVEMENT ?= 0.25
GROUNDED_EXPECTED_DONORS ?= usaid,eu,worldbank,state_department
GROUNDED_TAIL_EXPECTED_DONORS ?= eu,giz,un_agencies
GROUNDED_MIN_SEEDED_TOTAL ?= 1
ALLOW_BASELINE_REFRESH ?= 0
LLM_EVAL_SAMPLE_MAX_CASES ?= 2
LLM_EVAL_SAMPLE_SEED ?= 42
LLM_GROUNDED_STRICT_DONORS ?= usaid,worldbank
LLM_GROUNDED_STRICT_MIN_SEED_PER_FAMILY ?= 1
RBM_SAMPLE_IDS ?= rbm-usaid-ai-civil-service-kazakhstan,rbm-eu-youth-employment-jordan

deps-guard:
	$(PYTHON) scripts/dependency_contract_guard.py

qa-fast:
	$(PYTHON) -m ruff check grantflow/swarm/nodes/mel_specialist.py grantflow/swarm/nodes/architect_generation.py grantflow/core/strategies grantflow/tests/test_mel.py grantflow/tests/test_strategies.py grantflow/tests/test_contracts.py
	$(PYTHON) -m pytest grantflow/tests/test_mel.py grantflow/tests/test_strategies.py grantflow/tests/test_contracts.py -q
	$(MAKE) qa-hitl
	$(PYTHON) -m mypy grantflow/api grantflow/core/stores.py grantflow/swarm/versioning.py

qa-hitl:
	$(PYTHON) -m pytest grantflow/tests/test_integration.py -k "test_quality_summary_endpoint_aggregates_quality_signals or test_hitl_pause_resume_flow_supports_export_payload_and_export or test_hitl_reject_then_resume_flow_supports_export_payload_and_export or test_hitl_logframe_reject_then_resume_flow_supports_export_payload_and_export or test_hitl_mixed_checkpoints_reject_approve_flow_records_history_events or test_status_hitl_history_endpoint_lists_and_filters_events" -q

eval-grounded-ab:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
	$(PYTHON) -m grantflow.eval.harness \
		--cases-file $(GROUNDED_CASES_FILE) \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--suite-label grounded-eval \
		--text-out $(EVAL_ARTIFACTS_DIR)/grounded-eval-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/grounded-eval-report.json \
		--compare-to-baseline $(GROUNDED_BASELINE) \
		--comparison-text-out $(EVAL_ARTIFACTS_DIR)/grounded-regression-comparison.txt \
		--comparison-json-out $(EVAL_ARTIFACTS_DIR)/grounded-regression-comparison.json
	$(PYTHON) scripts/check_seeded_corpus.py \
		--json $(EVAL_ARTIFACTS_DIR)/grounded-eval-report.json \
		--label grounded-eval-seed \
		--expected-donors $(GROUNDED_EXPECTED_DONORS) \
		--min-seeded-total $(GROUNDED_MIN_SEEDED_TOTAL)
	$(PYTHON) -m grantflow.eval.harness \
		--cases-file $(GROUNDED_CASES_FILE) \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--suite-label grounded-ab-a \
		--skip-expectations \
		--text-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-a-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-a-report.json
	$(PYTHON) scripts/check_seeded_corpus.py \
		--json $(EVAL_ARTIFACTS_DIR)/grounded-ab-a-report.json \
		--label grounded-ab-a-seed \
		--expected-donors $(GROUNDED_EXPECTED_DONORS) \
		--min-seeded-total $(GROUNDED_MIN_SEEDED_TOTAL)
	$(PYTHON) -m grantflow.eval.harness \
		--cases-file $(GROUNDED_CASES_FILE) \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--suite-label grounded-ab-b \
		--skip-expectations \
		--force-no-architect-rag \
		--text-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-b-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-b-report.json
	$(PYTHON) scripts/check_seeded_corpus.py \
		--json $(EVAL_ARTIFACTS_DIR)/grounded-ab-b-report.json \
		--label grounded-ab-b-seed \
		--expected-donors $(GROUNDED_EXPECTED_DONORS) \
		--min-seeded-total $(GROUNDED_MIN_SEEDED_TOTAL)
	$(PYTHON) scripts/eval_ab_diff.py \
		--a-json $(EVAL_ARTIFACTS_DIR)/grounded-ab-a-report.json \
		--b-json $(EVAL_ARTIFACTS_DIR)/grounded-ab-b-report.json \
		--a-label architect_rag_on \
		--b-label architect_rag_off \
		--guard-donors $(GROUNDED_GUARD_DONORS) \
		--max-a-non-retrieval-rate $(GROUNDED_MAX_NON_RETRIEVAL) \
		--min-a-retrieval-grounded-rate $(GROUNDED_MIN_RETRIEVAL_GROUNDED) \
		--max-a-traceability-gap-rate $(GROUNDED_MAX_TRACEABILITY_GAP) \
		--min-a-non-retrieval-improvement-vs-b $(GROUNDED_MIN_NON_RETRIEVAL_IMPROVEMENT) \
		--min-a-retrieval-grounded-improvement-vs-b $(GROUNDED_MIN_RETRIEVAL_GROUNDED_IMPROVEMENT) \
		--text-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-diff.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/grounded-ab-diff.json
	$(PYTHON) scripts/build_grounded_gate_summary.py \
		--grounded-json $(EVAL_ARTIFACTS_DIR)/grounded-eval-report.json \
		--grounded-comparison-json $(EVAL_ARTIFACTS_DIR)/grounded-regression-comparison.json \
		--ab-diff-json $(EVAL_ARTIFACTS_DIR)/grounded-ab-diff.json \
		--expected-donors $(GROUNDED_EXPECTED_DONORS) \
		--min-seeded-total $(GROUNDED_MIN_SEEDED_TOTAL) \
		--out $(EVAL_ARTIFACTS_DIR)/grounded-gate-summary.md

eval-grounded-tail:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
	$(PYTHON) -m grantflow.eval.harness \
		--cases-file $(GROUNDED_TAIL_CASES_FILE) \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--suite-label grounded-tail-eval \
		--text-out $(EVAL_ARTIFACTS_DIR)/grounded-tail-eval-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/grounded-tail-eval-report.json \
		--compare-to-baseline $(GROUNDED_TAIL_BASELINE) \
		--comparison-text-out $(EVAL_ARTIFACTS_DIR)/grounded-tail-regression-comparison.txt \
		--comparison-json-out $(EVAL_ARTIFACTS_DIR)/grounded-tail-regression-comparison.json
	$(PYTHON) scripts/check_seeded_corpus.py \
		--json $(EVAL_ARTIFACTS_DIR)/grounded-tail-eval-report.json \
		--label grounded-tail-eval-seed \
		--expected-donors $(GROUNDED_TAIL_EXPECTED_DONORS) \
		--min-seeded-total $(GROUNDED_MIN_SEEDED_TOTAL)

eval-llm-sampled:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
	$(PYTHON) -m grantflow.eval.harness \
		--suite-label llm-eval-sampled \
		--force-llm \
		--force-architect-rag \
		--skip-expectations \
		--max-cases $(LLM_EVAL_SAMPLE_MAX_CASES) \
		--sample-seed $(LLM_EVAL_SAMPLE_SEED) \
		--text-out $(EVAL_ARTIFACTS_DIR)/llm-eval-sampled.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/llm-eval-sampled.json

eval-llm-grounded-strict:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
	$(PYTHON) -m grantflow.eval.harness \
		--suite-label llm-eval-grounded-strict \
		--cases-file $(LLM_GROUNDED_STRICT_CASES_FILE) \
		--donor-id $(LLM_GROUNDED_STRICT_DONORS) \
		--force-llm \
		--force-architect-rag \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--require-seed-readiness \
		--seed-readiness-min-per-family $(LLM_GROUNDED_STRICT_MIN_SEED_PER_FAMILY) \
		--text-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.json

eval-rbm-samples:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
	$(PYTHON) -m grantflow.eval.harness \
		--suite-label rbm-sample-eval \
		--sample-id $(RBM_SAMPLE_IDS) \
		--skip-expectations \
		--text-out $(EVAL_ARTIFACTS_DIR)/rbm-sample-eval.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/rbm-sample-eval.json

refresh-grounded-baseline:
	ALLOW_BASELINE_REFRESH=$(ALLOW_BASELINE_REFRESH) PYTHONPATH=. $(PYTHON) scripts/refresh_grounded_baseline.py \
		--cases-file $(GROUNDED_CASES_FILE) \
		--seed-rag-manifest $(GROUNDED_SEED_MANIFEST) \
		--out $(GROUNDED_BASELINE)
