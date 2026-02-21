# CI / Tests

This repository uses GitHub Actions to run in-process tests for the AidGraph loop convergence
using the in-memory LLM stub. The tests live at aidgraph/tests/test_loop_convergence.py
and exercise USAID and EU convergence under llm_mode.

To run locally:
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\\Scripts\\activate)
- pip install -r aidgraph/requirements.txt
- pytest aidgraph/tests/test_loop_convergence.py
