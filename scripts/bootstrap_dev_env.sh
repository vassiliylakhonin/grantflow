#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv/bin/python" ]]; then
  echo "Using existing .venv"
  PYTHON_BIN=".venv/bin/python"
else
  for candidate in python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "Creating .venv with $candidate"
      "$candidate" -m venv .venv
      break
    fi
  done

  if [[ ! -x ".venv/bin/python" ]]; then
    echo "ERROR: Python 3.11-3.13 is required." >&2
    exit 1
  fi

  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" -m pip install -U pip
"$PYTHON_BIN" -m pip install -r requirements-dev.txt

echo "Done. Activate with: source .venv/bin/activate"
