#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source scripts/feature-environment.sh >/dev/null 2>&1
set -euo pipefail
prefix=$(python -c 'import correctionlib,pathlib; print(pathlib.Path(correctionlib.__file__).parent)')
core=$(head -1 .build/feature-location.txt)
build=$(tail -1 .build/feature-location.txt)
cmake -S . -B "$build/sanitized" -DCMAKE_BUILD_TYPE=Release \
  -Dcorrectionlib_DIR="$prefix/cmake" -DSTUDY_SANITIZE=ON \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DRAPIDJSON_INCLUDE_DIR="$core/rapidjson/include" \
  -DCMAKE_BUILD_RPATH="$prefix/lib"
cmake --build "$build/sanitized" -j 2
export HISTOGRAM_STUDY_LIBRARY="$build/sanitized/libhistogram_nodes.so"
python -c 'from histogram_nodes import register_feature_nodes; register_feature_nodes(); from correctionlib.plugins import enable_discovery; enable_discovery(False); import pytest; raise SystemExit(pytest.main(["-q"]))'
