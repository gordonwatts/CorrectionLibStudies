#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source scripts/environment.sh >/dev/null 2>&1
set -euo pipefail
prefix=$(python -c 'import correctionlib,pathlib; print(pathlib.Path(correctionlib.__file__).parent)')
build_root=$(cat .build/location.txt)
cmake -S . -B "$build_root/sanitized" -DCMAKE_BUILD_TYPE=Release \
    -Dcorrectionlib_DIR="$prefix/cmake" -DSTUDY_SANITIZE=ON \
    -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
    -DRAPIDJSON_INCLUDE_DIR="$PWD/_deps/correctionlib/rapidjson/include" \
    -DCMAKE_BUILD_RPATH="$prefix/lib"
cmake --build "$build_root/sanitized" -j 2
python -c 'import sys; from correctionlib.plugins import enable_discovery, load_library; enable_discovery(False); load_library(sys.argv[1]); import pytest; raise SystemExit(pytest.main(["-q"]))' "$build_root/sanitized/libhistogram_nodes.so"
