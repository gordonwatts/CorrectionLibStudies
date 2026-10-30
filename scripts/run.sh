#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source scripts/environment.sh >/dev/null 2>&1
set -euo pipefail
label="${1:?Usage: bash scripts/run.sh NEW-LABEL}"
python -m pytest -q > results/tests.log 2>&1
python scripts/provenance.py
python scripts/benchmark.py "$label"
