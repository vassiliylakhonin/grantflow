# AidGraph: Grant Proposal Acceleration Platform

## Overview

AidGraph automates the creation of donor-compliant grant proposals using a hybrid AI system that combines isolated donor rulebases (RAG) with adversarial AI validation. By leveraging pre-loaded official documentation for each donor, AidGraph ensures that every output adheres to strict regulatory and logical requirements before human review.

## Features

- **Donor Strategy Templates**: USAID, EU, World Bank, and other major donors are supported with fully isolated RAG namespaces.
- **Adversarial Red Team**: A dedicated critic evaluates proposals for causal gaps, unrealistic assumptions, and missing cross‑cutting themes.
- **Standard Foreign Assistance Indicators (SFIA)**: MEL specialist generates compliant indicator assignments sourced directly from the donor’s official indicator handbook.
- **Human‑in‑the‑Loop (HITL)**: Checkpoint‑based approval workflow ensures that only verified proposals reach senior staff.
- **Prometheus‑ready Monitoring**: Optional integration for tracking proposal generation latency and quality metrics.
- **Modular Codebase**: Swappable agents allow rapid addition of new donors or evaluation criteria.

## Architecture Overview

### Core Components

- **Donor Strategy Pattern**: Isolated strategy classes per donor (e.g., `USAIDStrategy`, `EUStrategy`).
- **LangGraph State Machine**: Executes the proposal generation loop with conditional edges for red‑team re‑run up to three times until the proposal score reaches >=8.
- **ChromaDB RAG**: Namespace‑isolated vector stores for donor-specific documentation.
- **HITL (Human‑in‑the‑Loop)**: UUID‑tracked checkpoints for senior review and approval.
- **API Layer**: Simple Flask endpoint exposing proposal generation as a JSON‑POST API.

## Why AidGraph?

Traditional grant writing consumes weeks and tens of thousands of dollars in consulting fees. General‑purpose LLMs often hallucinate indicator codes or violate donor logical frameworks. AidGraph solves this by:

1. **Pre‑populating ChromaDB** with official donor documentation (e.g., USAID ADS 201, Standard Foreign Assistance Indicators, EU INTPA Logical Framework).
2. **Requiring a Red‑Team Critic** to score proposals out of 10, forcing iterative improvement before human review.
3. **Providing a transparent, reproducible workflow** that can be audited and versioned.

## Example cURL (Why it matters)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "input_context": {
      "strategic_goal": "Improve WASH infrastructure and local governance in rural Kenya",
      "target_beneficiaries": "50,000 women and children",
      "budget_usd": 5000000,
      "duration_months": 36
    }
  }' \
  https://api.aidgraph.dev/proposal/generate

**Why it matters:** The example shows a real donor scenario (USAID‑style), includes a clear impact statement, and leverages official SFIA indicators that the backend will retrieve from ChromaDB. This reassures fund managers that the proposal complies with donor‑specific rules, reducing audit risk and accelerating the review timeline.

## Development Trajectory

```bash
git clone https://github.com/vassiliylakhonin/aidgraph-prod
cd aidgraph-prod
pip install -r requirements.txt
aidegraph-init --donor USAID
```

## Contribution

Contributions are welcome! Please follow the standard pull‑request workflow:

```bash
git checkout -b feature/your-feature
# make changes, run tests, push
git push origin feature/your-feature
```

Feel free to open an issue for bugs or feature requests.

---