#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source scripts/feature-environment.sh >/dev/null 2>&1
set -euo pipefail
label="${1:?Usage: bash scripts/run-feature.sh NEW-LABEL}"
python -m pytest -q > results/feature-tests.log 2>&1
python scripts/feature-provenance.py
python scripts/benchmark-feature.py "$label"
