.PHONY: eval-grounded-ab

PYTHON ?= python3
EVAL_ARTIFACTS_DIR ?= eval-artifacts
GROUNDED_CASES_FILE ?= grantflow/eval/cases/grounded_cases.json
GROUNDED_SEED_MANIFEST ?= docs/rag_seed_corpus/ingest_manifest.jsonl
GROUNDED_GUARD_DONORS ?= usaid,eu,worldbank,state_department
GROUNDED_MAX_NON_RETRIEVAL ?= 0.25
GROUNDED_MIN_RETRIEVAL_GROUNDED ?= 0.75
GROUNDED_MAX_TRACEABILITY_GAP ?= 0.10
GROUNDED_MIN_NON_RETRIEVAL_IMPROVEMENT ?= 0.25
GROUNDED_MIN_RETRIEVAL_GROUNDED_IMPROVEMENT ?= 0.25
GROUNDED_EXPECTED_DONORS ?= usaid,eu,worldbank,state_department
GROUNDED_MIN_SEEDED_TOTAL ?= 1

eval-grounded-ab:
	mkdir -p $(EVAL_ARTIFACTS_DIR)
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
