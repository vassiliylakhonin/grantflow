.PHONY: deps-guard qa-fast qa-hitl preflight-prod-api preflight-prod-worker eval-grounded-ab eval-grounded-tail eval-llm-sampled eval-llm-grounded-strict eval-rbm-samples refresh-grounded-baseline demo-pack pilot-pack buyer-brief buyer-brief-refresh pilot-metrics pilot-metrics-refresh pilot-scorecard pilot-scorecard-refresh case-study-pack case-study-pack-refresh executive-pack executive-pack-refresh oem-pack oem-pack-refresh pilot-archive pilot-archive-refresh diligence-index diligence-index-refresh baseline-fill-template baseline-fill-template-refresh clean-demo-artifacts clean-demo-artifacts-dry-run latest-links latest-links-refresh pilot-handout pilot-handout-refresh smoke-demo-refresh latest-open-order latest-open-order-refresh pilot-refresh-fast verify-latest-stack verify-latest-stack-refresh release-demo-bundle buyer-demo-open buyer-demo-open-refresh

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
PILOT_SCORECARD_PILOT_DIR ?= $(PILOT_PACK_DIR)
PILOT_SCORECARD_OUT ?=
CASE_STUDY_PILOT_DIR ?= $(PILOT_PACK_DIR)
CASE_STUDY_CASE_DIR ?=
CASE_STUDY_PRESET_KEY ?=
CASE_STUDY_OUT_DIR ?= build/case-study-pack
EXECUTIVE_PACK_PILOT_DIR ?= $(PILOT_PACK_DIR)
EXECUTIVE_PACK_CASE_STUDY_DIR ?= $(CASE_STUDY_OUT_DIR)
EXECUTIVE_PACK_CASE_DIR ?= $(CASE_STUDY_CASE_DIR)
EXECUTIVE_PACK_PRESET_KEY ?= $(CASE_STUDY_PRESET_KEY)
EXECUTIVE_PACK_OUT_DIR ?= build/executive-pack
OEM_PACK_PILOT_DIR ?= $(PILOT_PACK_DIR)
OEM_PACK_EXECUTIVE_DIR ?= $(EXECUTIVE_PACK_OUT_DIR)
OEM_PACK_CASE_DIR ?= $(EXECUTIVE_PACK_CASE_DIR)
OEM_PACK_PRESET_KEY ?= $(EXECUTIVE_PACK_PRESET_KEY)
OEM_PACK_OUT_DIR ?= build/oem-pack
PILOT_ARCHIVE_PILOT_DIR ?= $(PILOT_PACK_DIR)
PILOT_ARCHIVE_EXECUTIVE_DIR ?= $(EXECUTIVE_PACK_OUT_DIR)
PILOT_ARCHIVE_OEM_DIR ?= $(OEM_PACK_OUT_DIR)
PILOT_ARCHIVE_OUT_DIR ?= build/pilot-archive
PILOT_ARCHIVE_NAME ?=
PILOT_ARCHIVE_INCLUDE_OEM ?= 1
DILIGENCE_INDEX_BUILD_DIR ?= build
DILIGENCE_INDEX_OUT ?= build/diligence-index.md
BASELINE_TEMPLATE_PILOT_DIR ?= $(PILOT_PACK_DIR)
BASELINE_TEMPLATE_METRICS_CSV ?=
BASELINE_TEMPLATE_CSV_OUT ?=
BASELINE_TEMPLATE_MD_OUT ?=
CLEAN_DEMO_ARTIFACTS_BUILD_DIR ?= build
LATEST_LINKS_BUILD_DIR ?= build
PILOT_HANDOUT_PILOT_DIR ?= $(PILOT_PACK_DIR)
PILOT_HANDOUT_EXECUTIVE_DIR ?= $(EXECUTIVE_PACK_OUT_DIR)
PILOT_HANDOUT_PRESET_KEY ?= $(CASE_STUDY_PRESET_KEY)
PILOT_HANDOUT_CASE_DIR ?= $(CASE_STUDY_CASE_DIR)
PILOT_HANDOUT_OUT ?= build/pilot-handout.md
LATEST_OPEN_ORDER_BUILD_DIR ?= build
LATEST_OPEN_ORDER_OUT ?= build/latest-open-order.md
VERIFY_LATEST_STACK_BUILD_DIR ?= build
RELEASE_DEMO_BUNDLE_BUILD_DIR ?= build
RELEASE_DEMO_BUNDLE_OUT_DIR ?= build/release-demo-bundle
RELEASE_DEMO_BUNDLE_NAME ?= grantflow-demo-bundle
BUYER_DEMO_OPEN_BUILD_DIR ?= build
BUYER_DEMO_OPEN_MODE ?= print

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

pilot-scorecard:
	$(PYTHON) scripts/pilot_scorecard.py \
		--pilot-pack-dir $(PILOT_SCORECARD_PILOT_DIR) \
		$(if $(strip $(PILOT_SCORECARD_OUT)),--output $(PILOT_SCORECARD_OUT),)

pilot-scorecard-refresh: pilot-metrics-refresh buyer-brief
	$(MAKE) pilot-scorecard PILOT_SCORECARD_PILOT_DIR=$(PILOT_PACK_DIR) PILOT_SCORECARD_OUT=$(PILOT_SCORECARD_OUT)

case-study-pack:
	$(PYTHON) scripts/case_study_pack.py \
		--pilot-pack-dir $(CASE_STUDY_PILOT_DIR) \
		$(if $(strip $(CASE_STUDY_CASE_DIR)),--case-dir $(CASE_STUDY_CASE_DIR),) \
		$(if $(strip $(CASE_STUDY_PRESET_KEY)),--preset-key $(CASE_STUDY_PRESET_KEY),) \
		--output-dir $(CASE_STUDY_OUT_DIR)

case-study-pack-refresh: pilot-scorecard-refresh
	$(MAKE) case-study-pack CASE_STUDY_PILOT_DIR=$(PILOT_PACK_DIR) CASE_STUDY_CASE_DIR=$(CASE_STUDY_CASE_DIR) CASE_STUDY_PRESET_KEY=$(CASE_STUDY_PRESET_KEY) CASE_STUDY_OUT_DIR=$(CASE_STUDY_OUT_DIR)

executive-pack:
	$(PYTHON) scripts/executive_pack.py \
		--pilot-pack-dir $(EXECUTIVE_PACK_PILOT_DIR) \
		--case-study-dir $(EXECUTIVE_PACK_CASE_STUDY_DIR) \
		$(if $(strip $(EXECUTIVE_PACK_CASE_DIR)),--case-dir $(EXECUTIVE_PACK_CASE_DIR),) \
		$(if $(strip $(EXECUTIVE_PACK_PRESET_KEY)),--preset-key $(EXECUTIVE_PACK_PRESET_KEY),) \
		--output-dir $(EXECUTIVE_PACK_OUT_DIR)

executive-pack-refresh: case-study-pack-refresh
	$(MAKE) executive-pack EXECUTIVE_PACK_PILOT_DIR=$(PILOT_PACK_DIR) EXECUTIVE_PACK_CASE_STUDY_DIR=$(CASE_STUDY_OUT_DIR) EXECUTIVE_PACK_CASE_DIR=$(CASE_STUDY_CASE_DIR) EXECUTIVE_PACK_PRESET_KEY=$(CASE_STUDY_PRESET_KEY) EXECUTIVE_PACK_OUT_DIR=$(EXECUTIVE_PACK_OUT_DIR)

oem-pack:
	$(PYTHON) scripts/oem_pack.py \
		--pilot-pack-dir $(OEM_PACK_PILOT_DIR) \
		--executive-pack-dir $(OEM_PACK_EXECUTIVE_DIR) \
		$(if $(strip $(OEM_PACK_CASE_DIR)),--case-dir $(OEM_PACK_CASE_DIR),) \
		$(if $(strip $(OEM_PACK_PRESET_KEY)),--preset-key $(OEM_PACK_PRESET_KEY),) \
		--output-dir $(OEM_PACK_OUT_DIR)

oem-pack-refresh: executive-pack-refresh
	$(MAKE) oem-pack OEM_PACK_PILOT_DIR=$(PILOT_PACK_DIR) OEM_PACK_EXECUTIVE_DIR=$(EXECUTIVE_PACK_OUT_DIR) OEM_PACK_CASE_DIR=$(EXECUTIVE_PACK_CASE_DIR) OEM_PACK_PRESET_KEY=$(EXECUTIVE_PACK_PRESET_KEY) OEM_PACK_OUT_DIR=$(OEM_PACK_OUT_DIR)

pilot-archive:
	$(PYTHON) scripts/pilot_archive.py \
		--pilot-pack-dir $(PILOT_ARCHIVE_PILOT_DIR) \
		--executive-pack-dir $(PILOT_ARCHIVE_EXECUTIVE_DIR) \
		--oem-pack-dir $(PILOT_ARCHIVE_OEM_DIR) \
		--output-dir $(PILOT_ARCHIVE_OUT_DIR) \
		$(if $(strip $(PILOT_ARCHIVE_NAME)),--archive-name $(PILOT_ARCHIVE_NAME),) \
		$(if $(filter 1 true TRUE yes YES,$(PILOT_ARCHIVE_INCLUDE_OEM)),--include-oem,)

pilot-archive-refresh: oem-pack-refresh
	$(MAKE) pilot-archive PILOT_ARCHIVE_PILOT_DIR=$(PILOT_PACK_DIR) PILOT_ARCHIVE_EXECUTIVE_DIR=$(EXECUTIVE_PACK_OUT_DIR) PILOT_ARCHIVE_OEM_DIR=$(OEM_PACK_OUT_DIR) PILOT_ARCHIVE_OUT_DIR=$(PILOT_ARCHIVE_OUT_DIR) PILOT_ARCHIVE_NAME=$(PILOT_ARCHIVE_NAME) PILOT_ARCHIVE_INCLUDE_OEM=$(PILOT_ARCHIVE_INCLUDE_OEM)

diligence-index:
	$(PYTHON) scripts/diligence_index.py \
		--build-dir $(DILIGENCE_INDEX_BUILD_DIR) \
		--output $(DILIGENCE_INDEX_OUT)

diligence-index-refresh: pilot-archive-refresh
	$(MAKE) diligence-index DILIGENCE_INDEX_BUILD_DIR=$(DILIGENCE_INDEX_BUILD_DIR) DILIGENCE_INDEX_OUT=$(DILIGENCE_INDEX_OUT)

baseline-fill-template:
	$(PYTHON) scripts/baseline_fill_template.py \
		--pilot-pack-dir $(BASELINE_TEMPLATE_PILOT_DIR) \
		$(if $(strip $(BASELINE_TEMPLATE_METRICS_CSV)),--metrics-csv $(BASELINE_TEMPLATE_METRICS_CSV),) \
		$(if $(strip $(BASELINE_TEMPLATE_CSV_OUT)),--csv-out $(BASELINE_TEMPLATE_CSV_OUT),) \
		$(if $(strip $(BASELINE_TEMPLATE_MD_OUT)),--md-out $(BASELINE_TEMPLATE_MD_OUT),)

baseline-fill-template-refresh: pilot-metrics-refresh
	$(MAKE) baseline-fill-template BASELINE_TEMPLATE_PILOT_DIR=$(PILOT_PACK_DIR) BASELINE_TEMPLATE_METRICS_CSV=$(BASELINE_TEMPLATE_METRICS_CSV) BASELINE_TEMPLATE_CSV_OUT=$(BASELINE_TEMPLATE_CSV_OUT) BASELINE_TEMPLATE_MD_OUT=$(BASELINE_TEMPLATE_MD_OUT)

clean-demo-artifacts:
	$(PYTHON) scripts/clean_demo_artifacts.py \
		--build-dir $(CLEAN_DEMO_ARTIFACTS_BUILD_DIR)

clean-demo-artifacts-dry-run:
	$(PYTHON) scripts/clean_demo_artifacts.py \
		--build-dir $(CLEAN_DEMO_ARTIFACTS_BUILD_DIR) \
		--dry-run

latest-links:
	$(PYTHON) scripts/latest_links.py \
		--build-dir $(LATEST_LINKS_BUILD_DIR)

latest-links-refresh: diligence-index-refresh
	$(MAKE) latest-links LATEST_LINKS_BUILD_DIR=$(LATEST_LINKS_BUILD_DIR)

pilot-handout:
	$(PYTHON) scripts/pilot_handout.py \
		--pilot-pack-dir $(PILOT_HANDOUT_PILOT_DIR) \
		--executive-pack-dir $(PILOT_HANDOUT_EXECUTIVE_DIR) \
		$(if $(strip $(PILOT_HANDOUT_PRESET_KEY)),--preset-key $(PILOT_HANDOUT_PRESET_KEY),) \
		$(if $(strip $(PILOT_HANDOUT_CASE_DIR)),--case-dir $(PILOT_HANDOUT_CASE_DIR),) \
		--output $(PILOT_HANDOUT_OUT)

pilot-handout-refresh: latest-links-refresh
	$(MAKE) pilot-handout PILOT_HANDOUT_PILOT_DIR=$(PILOT_PACK_DIR) PILOT_HANDOUT_EXECUTIVE_DIR=$(EXECUTIVE_PACK_OUT_DIR) PILOT_HANDOUT_PRESET_KEY=$(PILOT_HANDOUT_PRESET_KEY) PILOT_HANDOUT_CASE_DIR=$(PILOT_HANDOUT_CASE_DIR) PILOT_HANDOUT_OUT=$(PILOT_HANDOUT_OUT)

smoke-demo-refresh: pilot-handout-refresh
	@echo "smoke demo refresh complete"

pilot-refresh-fast: executive-pack-refresh
	$(MAKE) latest-links LATEST_LINKS_BUILD_DIR=$(LATEST_LINKS_BUILD_DIR)
	$(MAKE) pilot-handout PILOT_HANDOUT_PILOT_DIR=$(PILOT_PACK_DIR) PILOT_HANDOUT_EXECUTIVE_DIR=$(EXECUTIVE_PACK_OUT_DIR) PILOT_HANDOUT_PRESET_KEY=$(PILOT_HANDOUT_PRESET_KEY) PILOT_HANDOUT_CASE_DIR=$(PILOT_HANDOUT_CASE_DIR) PILOT_HANDOUT_OUT=$(PILOT_HANDOUT_OUT)
	$(MAKE) latest-open-order LATEST_OPEN_ORDER_BUILD_DIR=$(LATEST_OPEN_ORDER_BUILD_DIR) LATEST_OPEN_ORDER_OUT=$(LATEST_OPEN_ORDER_OUT)
	@echo "pilot refresh fast complete"

latest-open-order:
	$(PYTHON) scripts/latest_open_order.py \
		--build-dir $(LATEST_OPEN_ORDER_BUILD_DIR) \
		--output $(LATEST_OPEN_ORDER_OUT)

latest-open-order-refresh: latest-links-refresh
	$(MAKE) latest-open-order LATEST_OPEN_ORDER_BUILD_DIR=$(LATEST_OPEN_ORDER_BUILD_DIR) LATEST_OPEN_ORDER_OUT=$(LATEST_OPEN_ORDER_OUT)

verify-latest-stack:
	$(PYTHON) scripts/verify_latest_stack.py \
		--build-dir $(VERIFY_LATEST_STACK_BUILD_DIR)

verify-latest-stack-refresh: latest-open-order-refresh
	$(MAKE) verify-latest-stack VERIFY_LATEST_STACK_BUILD_DIR=$(VERIFY_LATEST_STACK_BUILD_DIR)

release-demo-bundle: verify-latest-stack-refresh
	$(PYTHON) scripts/release_demo_bundle.py \
		--build-dir $(RELEASE_DEMO_BUNDLE_BUILD_DIR) \
		--output-dir $(RELEASE_DEMO_BUNDLE_OUT_DIR) \
		--bundle-name $(RELEASE_DEMO_BUNDLE_NAME)

buyer-demo-open:
	$(PYTHON) scripts/buyer_demo_open.py \
		--build-dir $(BUYER_DEMO_OPEN_BUILD_DIR) \
		--mode $(BUYER_DEMO_OPEN_MODE)

buyer-demo-open-refresh: pilot-refresh-fast
	$(MAKE) buyer-demo-open BUYER_DEMO_OPEN_BUILD_DIR=$(BUYER_DEMO_OPEN_BUILD_DIR) BUYER_DEMO_OPEN_MODE=$(BUYER_DEMO_OPEN_MODE)
