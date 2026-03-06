.PHONY: deps-guard qa-fast qa-hitl preflight-prod-api preflight-prod-worker eval-grounded-ab eval-grounded-tail eval-llm-sampled eval-llm-grounded-strict eval-rbm-samples refresh-grounded-baseline demo-pack pilot-pack buyer-brief buyer-brief-refresh pilot-metrics pilot-metrics-refresh

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
EVAL_ARTIFACTS_DIR ?= eval-artifacts
GROUNDED_CASES_FILE ?= grantflow/eval/cases/grounded_cases.json
GROUNDED_TAIL_CASES_FILE ?= grantflow/eval/cases/grounded_tail_cases.json
LLM_GROUNDED_STRICT_CASES_FILE ?= grantflow/eval/cases/llm_grounded_strict_cases.json
LLM_GROUNDED_STRICT_BASELINE ?= grantflow/eval/fixtures/llm_grounded_strict_regression_snapshot.json
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
LLM_GROUNDED_STRICT_DONORS ?= usaid,eu,worldbank,giz,state_department
LLM_GROUNDED_STRICT_MIN_SEED_PER_FAMILY ?= 1
LLM_GROUNDED_STRICT_GATE_THRESHOLDS ?= grantflow/eval/fixtures/llm_grounded_strict_donor_gate_thresholds.json
RBM_SAMPLE_IDS ?= rbm-usaid-ai-civil-service-kazakhstan,rbm-eu-youth-employment-jordan
DEMO_PACK_DIR ?= build/demo-pack
DEMO_PACK_API_BASE ?= http://127.0.0.1:8000
DEMO_PACK_API_KEY ?=
DEMO_PACK_PRESET_KEYS ?= usaid_gov_ai_kazakhstan,eu_digital_governance_moldova,worldbank_public_sector_uzbekistan
DEMO_PACK_HITL_PRESET_KEY ?= usaid_gov_ai_kazakhstan
DEMO_PACK_LLM_MODE ?= 0
DEMO_PACK_ARCHITECT_RAG_ENABLED ?= 0
PILOT_PACK_DIR ?= build/pilot-pack
PILOT_PACK_DEMO_DIR ?= $(DEMO_PACK_DIR)
PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO ?= 0
BUYER_BRIEF_PILOT_DIR ?= $(PILOT_PACK_DIR)
BUYER_BRIEF_OUT ?=
PILOT_METRICS_PILOT_DIR ?= $(PILOT_PACK_DIR)
PILOT_METRICS_CSV_OUT ?=
PILOT_METRICS_MD_OUT ?=

deps-guard:
	$(PYTHON) scripts/dependency_contract_guard.py

qa-fast:
	$(PYTHON) -m ruff check grantflow scripts
	$(PYTHON) -m black --check grantflow/eval grantflow/core/job_runner.py scripts/build_llm_eval_summary.py
	$(PYTHON) -m pytest grantflow/tests/test_mel.py grantflow/tests/test_strategies.py grantflow/tests/test_contracts.py -q
	$(MAKE) qa-hitl
	$(PYTHON) -m mypy grantflow

qa-hitl:
	$(PYTHON) -m pytest grantflow/tests/test_integration.py -k "test_quality_summary_endpoint_aggregates_quality_signals or test_hitl_pause_resume_flow_supports_export_payload_and_export or test_hitl_reject_then_resume_flow_supports_export_payload_and_export or test_hitl_logframe_reject_then_resume_flow_supports_export_payload_and_export or test_hitl_mixed_checkpoints_reject_approve_flow_records_history_events or test_status_hitl_history_endpoint_lists_and_filters_events" -q

preflight-prod-api:
	$(PYTHON) scripts/preflight_prod_config.py --role api

preflight-prod-worker:
	$(PYTHON) scripts/preflight_prod_config.py --role worker

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
		--compare-to-baseline $(LLM_GROUNDED_STRICT_BASELINE) \
		--comparison-text-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-comparison.txt \
		--comparison-json-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-comparison.json \
		--text-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.txt \
		--json-out $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.json
	$(PYTHON) scripts/check_llm_grounded_strict_donor_gate.py \
		--report-json $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.json \
		--required-donors $(LLM_GROUNDED_STRICT_DONORS) \
		--thresholds-json $(LLM_GROUNDED_STRICT_GATE_THRESHOLDS) \
		--fail-on-skipped-exploratory \
		--out-json $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-donor-gate.json \
		--out-text $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-donor-gate.txt \
		--out-md $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-comment.md
	$(PYTHON) scripts/build_llm_eval_summary.py \
		--report-json $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-report.json \
		--comparison-json $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-comparison.json \
		--gate-json $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-donor-gate.json \
		--title "LLM Grounded Strict Summary" \
		--out-md $(EVAL_ARTIFACTS_DIR)/llm-eval-grounded-strict-summary.md

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

demo-pack:
	mkdir -p $(DEMO_PACK_DIR)
	$(PYTHON) scripts/demo_pack.py \
		--api-base $(DEMO_PACK_API_BASE) \
		--output-dir $(DEMO_PACK_DIR) \
		--api-key "$(DEMO_PACK_API_KEY)" \
		--preset-keys $(DEMO_PACK_PRESET_KEYS) \
		--hitl-preset-key $(DEMO_PACK_HITL_PRESET_KEY) \
		$(if $(filter 1 true TRUE yes YES,$(DEMO_PACK_LLM_MODE)),--llm-mode,) \
		$(if $(filter 1 true TRUE yes YES,$(DEMO_PACK_ARCHITECT_RAG_ENABLED)),--architect-rag-enabled,)

pilot-pack: demo-pack
	mkdir -p $(PILOT_PACK_DIR)
	$(PYTHON) scripts/pilot_pack.py \
		--demo-pack-dir $(PILOT_PACK_DEMO_DIR) \
		--output-dir $(PILOT_PACK_DIR) \
		$(if $(filter 1 true TRUE yes YES,$(PILOT_PACK_INCLUDE_PRODUCTIZATION_MEMO)),--include-productization-memo,)

buyer-brief:
	$(PYTHON) scripts/buyer_brief.py \
		--pilot-pack-dir $(BUYER_BRIEF_PILOT_DIR) \
		$(if $(strip $(BUYER_BRIEF_OUT)),--output $(BUYER_BRIEF_OUT),)

buyer-brief-refresh: pilot-pack
	$(MAKE) buyer-brief BUYER_BRIEF_PILOT_DIR=$(PILOT_PACK_DIR) BUYER_BRIEF_OUT=$(BUYER_BRIEF_OUT)

pilot-metrics:
	$(PYTHON) scripts/pilot_metrics.py \
		--pilot-pack-dir $(PILOT_METRICS_PILOT_DIR) \
		$(if $(strip $(PILOT_METRICS_CSV_OUT)),--csv-out $(PILOT_METRICS_CSV_OUT),) \
		$(if $(strip $(PILOT_METRICS_MD_OUT)),--md-out $(PILOT_METRICS_MD_OUT),)

pilot-metrics-refresh: pilot-pack
	$(MAKE) pilot-metrics PILOT_METRICS_PILOT_DIR=$(PILOT_PACK_DIR) PILOT_METRICS_CSV_OUT=$(PILOT_METRICS_CSV_OUT) PILOT_METRICS_MD_OUT=$(PILOT_METRICS_MD_OUT)
